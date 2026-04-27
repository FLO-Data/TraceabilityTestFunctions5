import logging
import azure.functions as func
import pyodbc
import json
import asyncio
import concurrent.futures
import datetime
from typing import Dict, Any
from shared_utils import get_connection_string


bp = func.Blueprint()


ALLOWED_STATUSES = {"OK", "NOK"}
DEFAULT_STATUS = "OK"


def _normalize_status(raw_status: Any) -> str:
    """Normalize status to 'OK' / 'NOK'. Defaults to 'OK' if missing/invalid.

    Trigger trg_Control_Station_Complete na DB strane vyhodnocuje
    Control_check podľa status='OK' (najnovší záznam per station). NOK
    záznamy idu do tabulky pre auditnú stopu, ale do počtu sa neráta.
    """
    if raw_status is None:
        return DEFAULT_STATUS
    s = str(raw_status).strip().upper()
    return s if s in ALLOWED_STATUSES else DEFAULT_STATUS


def _parse_timestamp(raw: Any) -> datetime.datetime:
    """Parse ISO timestamp from request to a Python datetime.

    Dôvod: pyodbc + MSSQL datetime má presnosť 3 desatinných miest.
    Posielať ISO string s mikrosekundami (napr. '2026-04-27T07:53:00.123456')
    spôsobí 'Conversion failed' (chyba 241). Parsovaním na native datetime
    + odovzdaním cez parameter pyodbc serializuje hodnotu binárne a
    SQL Server ju akceptuje vždy.
    """
    if isinstance(raw, datetime.datetime):
        return raw
    if not raw:
        return datetime.datetime.utcnow().replace(microsecond=0)
    s = str(raw).strip()
    # JS toISOString() končí 'Z' — Python <3.11 to v fromisoformat nepozná
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        logging.warning(f"Cannot parse check_timestamp={raw!r}, using utcnow()")
        return datetime.datetime.utcnow().replace(microsecond=0)
    # MSSQL datetime má presnosť 3 ms — orežeme aby sme nestrácali pri konverzii
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    # zaokrúhlime mikrosekundy na milisekundy (3 digit)
    micro = (dt.microsecond // 1000) * 1000
    return dt.replace(microsecond=micro)


async def insert_control_station(data: Dict[str, Any], conn_str: str) -> None:
    """Insert control station data into database using a separate thread."""
    station_id = data.get("station_id")
    part_id = data.get("part_id")
    sample = data.get("sample", 1)
    check_timestamp = _parse_timestamp(data.get("check_timestamp"))
    shipping_id = data.get("shipping_id")
    operator_id = data.get("operator_id") or data.get("employee_id")
    part_type = data.get("part_type")
    melt = data.get("melt")
    control_group_id = data.get("control_group_id")
    status = _normalize_status(data.get("status"))

    with concurrent.futures.ThreadPoolExecutor() as pool:
        await asyncio.get_event_loop().run_in_executor(
            pool,
            execute_insert,
            conn_str,
            station_id,
            part_id,
            sample,
            check_timestamp,
            shipping_id,
            operator_id,
            part_type,
            melt,
            control_group_id,
            status,
        )


def execute_insert(conn_str: str, station_id: int, part_id: str, sample: int,
                   check_timestamp: datetime.datetime, shipping_id: str, operator_id: str,
                   part_type: int, melt: str, control_group_id: int,
                   status: str) -> None:
    """Execute insert into Control_Station."""
    try:
        with pyodbc.connect(conn_str, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO dbo.Control_Station (
                    station_id,
                    part_id,
                    sample,
                    check_timestamp,
                    shipping_id,
                    operator_id,
                    part_type,
                    melt,
                    control_group_id,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                station_id,
                part_id,
                sample,
                check_timestamp,
                shipping_id,
                operator_id,
                part_type,
                melt,
                control_group_id,
                status,
            )
            conn.commit()
            logging.info(
                f"Control_Station insert ok for part_id={part_id} "
                f"station_id={station_id} status={status}"
            )
    except Exception as exc:
        logging.error(f"Control_Station insert failed for part_id {part_id}: {exc}", exc_info=True)
        raise


@bp.function_name(name="ControlStationInsertHttpFunc")
@bp.route(route="ControlStationInsert", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def http_function(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint to insert control station data."""
    logging.info("ControlStationInsert Azure function triggered.")

    try:
        if not req.headers.get('content-type', '').startswith('application/json'):
            return func.HttpResponse(
                body=json.dumps({"error": "Content-Type must be application/json"}),
                mimetype="application/json",
                status_code=400
            )

        req_body = req.get_json()
        part_id = req_body.get("part_id")
        station_id = req_body.get("station_id")

        if not part_id or station_id is None:
            return func.HttpResponse(
                body=json.dumps({"error": "Request body must contain 'part_id' and 'station_id'"}),
                mimetype="application/json",
                status_code=400
            )

        try:
            req_body["station_id"] = int(station_id)
        except (ValueError, TypeError):
            return func.HttpResponse(
                body=json.dumps({"error": "station_id must be numeric"}),
                mimetype="application/json",
                status_code=400
            )

        if "sample" in req_body:
            try:
                req_body["sample"] = int(req_body["sample"])
            except (ValueError, TypeError):
                req_body["sample"] = 1

        if "control_group_id" in req_body and req_body["control_group_id"] is not None:
            try:
                req_body["control_group_id"] = int(req_body["control_group_id"])
            except (ValueError, TypeError):
                req_body["control_group_id"] = None

        conn_str = get_connection_string()
        await insert_control_station(req_body, conn_str)

        return func.HttpResponse(
            body=json.dumps({"message": "Control station data inserted successfully"}),
            mimetype="application/json",
            status_code=200
        )
    except ValueError as ve:
        logging.error(f"ValueError in ControlStationInsert: {ve}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": str(ve)}),
            mimetype="application/json",
            status_code=400
        )
    except pyodbc.Error as db_error:
        logging.error(f"Database error in ControlStationInsert: {db_error}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "Database connection error. Check logs for details."}),
            mimetype="application/json",
            status_code=500
        )
    except Exception as e:
        logging.error(f"Unhandled error in ControlStationInsert: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "An internal server error occurred. Check logs for details."}),
            mimetype="application/json",
            status_code=500
        )
