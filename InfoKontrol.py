"""
HTTP GET: přehled posledních stavů kontrol (15-20) pro part_id.
Použití pro stránku „Info režim kontrol“ ve WebApp.
"""
import json
import logging
import azure.functions as func
import pyodbc
from shared_utils import get_connection_string

bp = func.Blueprint()

# Musí být v synchronu s app.py CONTROL_WORKPLACES + workplaceConfig.stationIds
STATION_DEFS = [
    (15, "KKK_Povrch", "KKK_povrch", True, True),   # try / kvalita
    (16, "KKK_Rozmer", "KKK_rozměr", True, True),
    (17, "KKK_Tvrdost", "KKK_tvrdost", True, True),
    (18, "LAB_Tvrdost", "LAB_tvrdost", True, True),
    (19, "LAB_Trhacka", "LAB_trhačka", False, True),
    (20, "LAB_Makro", "LAB_makro", False, True),
]


def fetch_info(part_id: str) -> dict:
    conn_str = get_connection_string()
    with pyodbc.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT CASE WHEN
                    EXISTS (SELECT 1 FROM dbo.part_status WHERE part_id = ?)
                    OR EXISTS (SELECT 1 FROM dbo.traceability_log WHERE part_id = ?)
                    OR EXISTS (SELECT 1 FROM dbo.Control_Station WHERE part_id = ?)
                THEN 1 ELSE 0 END
                """,
                (part_id, part_id, part_id),
            )
            part_found_row = cur.fetchone()
            if not part_found_row or int(part_found_row[0]) != 1:
                return {
                    "part_id": part_id,
                    "part_found": False,
                    "message": (
                        "Díl s tímto číslem v databázi traceability neexistuje "
                        "(není v part_status, ani v logu procesů, ani v kontrolách)."
                    ),
                    "part_status_found": False,
                    "last_process_station_id": None,
                    "last_process_status": None,
                    "control_check": False,
                    "quality_check": False,
                    "controls": [],
                    "missing_labels_for_tryskani": [],
                    "missing_labels_for_kvalita": [],
                }

            cur.execute(
                """
                SELECT last_status, station_id, Control_check, Quality_check
                FROM dbo.part_status
                WHERE part_id = ?
                """,
                (part_id,),
            )
            ps = cur.fetchone()

            cur.execute(
                """
                SELECT x.station_id, x.status, x.check_timestamp, x.operator_id
                FROM (
                    SELECT station_id, status, check_timestamp, operator_id, id,
                           ROW_NUMBER() OVER (
                               PARTITION BY part_id, station_id
                               ORDER BY check_timestamp DESC, id DESC
                           ) AS rn
                    FROM dbo.Control_Station
                    WHERE part_id = ? AND station_id BETWEEN 15 AND 20
                ) x
                WHERE x.rn = 1
                ORDER BY x.station_id
                """,
                (part_id,),
            )
            latest_rows = {
                int(r[0]): (r[1], r[2], r[3]) for r in cur.fetchall()
            }

    by_station = {}
    for sid, wid, label, for_try, for_kk in STATION_DEFS:
        st, ts, op_raw = latest_rows.get(sid, (None, None, None))
        st_up = (st or "").strip().upper() if st else None
        if st_up not in ("OK", "NOK"):
            st_up = None
        op_str = (str(op_raw).strip() if op_raw is not None else "") or None
        by_station[sid] = {
            "station_id": sid,
            "workplace_id": wid,
            "label": label,
            "status": st_up,
            "check_timestamp": ts.isoformat() if ts else None,
            "operator_id": op_str,
            "counts_for_tryskani_gate": for_try,
            "counts_for_kvalita_gate": for_kk,
            "missing_for_tryskani": for_try and st_up != "OK",
            "missing_for_kvalita": for_kk and st_up != "OK",
        }

    control_check = bool(ps[2]) if ps and ps[2] is not None else False
    quality_check = bool(ps[3]) if ps and ps[3] is not None else False

    missing_try = [by_station[s]["label"] for s in (15, 16, 17, 18) if by_station[s]["missing_for_tryskani"]]
    missing_kk = [by_station[s]["label"] for s in (15, 16, 17, 18, 19, 20) if by_station[s]["missing_for_kvalita"]]

    return {
        "part_id": part_id,
        "part_found": True,
        "part_status_found": ps is not None,
        "last_process_station_id": str(ps[1]) if ps and ps[1] is not None else None,
        "last_process_status": ps[0] if ps else None,
        "control_check": control_check,
        "quality_check": quality_check,
        "controls": list(by_station.values()),
        "missing_labels_for_tryskani": missing_try,
        "missing_labels_for_kvalita": missing_kk,
    }


@bp.function_name(name="InfoKontrol")
@bp.route(route="InfoKontrol", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def info_kontrol(req: func.HttpRequest) -> func.HttpResponse:
    part_id = req.params.get("part_id")
    if not part_id:
        try:
            body = req.get_json()
        except ValueError:
            body = None
        if body:
            part_id = body.get("part_id")
    part_id = (part_id or "").strip()
    if not part_id:
        return func.HttpResponse(
            json.dumps({"error": "Missing part_id"}),
            status_code=400,
            mimetype="application/json",
        )
    try:
        payload = fetch_info(part_id)
        return func.HttpResponse(
            json.dumps(payload, default=str),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.exception("InfoKontrol failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
