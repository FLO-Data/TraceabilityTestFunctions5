import json
import logging
import pyodbc
import azure.functions as func
import concurrent.futures
from typing import Dict, Tuple, Any, Optional, List
from shared_utils import get_connection_string

# Configure logging
logging.basicConfig(level=logging.INFO)

bp = func.Blueprint()


@bp.function_name(name="GetInfoRezim2")
@bp.route(route="InfoRezim2", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def InfoRezim2(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("InfoRezim2 function processing a request")

    input_value = (
        req.params.get("value")
        or req.params.get("input")
        or req.params.get("code")
        or req.params.get("part_id")
        or req.params.get("shipping_id")
    )

    if not input_value:
        try:
            req_body = req.get_json()
            logging.info(f"Attempting to get value from request body: {req_body}")
        except ValueError:
            logging.warning("No JSON body in request")
        else:
            input_value = (
                req_body.get("value")
                or req_body.get("input")
                or req_body.get("code")
                or req_body.get("part_id")
                or req_body.get("shipping_id")
            )

    if not input_value:
        logging.error("No input value provided in request")
        return func.HttpResponse(
            "Please pass value in the query string or request body",
            status_code=400
        )

    logging.info(f"Processing request for value: {input_value}")

    try:
        conn_str = get_connection_string()
        logging.info("Successfully built connection string")
    except Exception as e:
        logging.error(f"Error building connection string: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Database configuration error"}),
            status_code=500,
            mimetype="application/json"
        )

    try:
        response_data, status_code = process_request(input_value, conn_str)

        if status_code != 200:
            return func.HttpResponse(
                json.dumps(response_data),
                status_code=status_code,
                mimetype="application/json"
            )

        response = json.dumps(response_data, default=str)
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

    return func.HttpResponse(
        response,
        status_code=200,
        mimetype="application/json"
    )


def fetch_parts_by_shipping(conn_str: str, input_value: str) -> Optional[List[Dict[str, Any]]]:
    """Get parts that share shipping_id on station 1 and enrich with status and protocols."""
    query = """
        WITH target_shipping AS (
            SELECT DISTINCT h.shipping_id
            FROM Traceability_TEST.dbo.h_part_status h
            WHERE h.station_id = '1'
              AND (h.shipping_id = ? OR h.part_id = ?)
        ),
        parts_in_shipping AS (
            SELECT DISTINCT h.part_id, h.shipping_id
            FROM Traceability_TEST.dbo.h_part_status h
            JOIN target_shipping ts ON ts.shipping_id = h.shipping_id
            WHERE h.station_id = '1'
        )
        SELECT 
            p.part_id,
            p.shipping_id AS source_shipping_id,
            ps.last_status,
            ps.status_timestamp,
            ps.shipping_id AS current_GiBo,
            ps.station_id AS current_station_id,
            cs.station_name AS current_station_name,
            ps.[melt] AS melt,
            "12345" AS part_type,
            h999.qc_forging_protocol,
            h999.lab_forging_protocol
        FROM parts_in_shipping p
        LEFT JOIN Traceability_TEST.dbo.part_status ps
            ON ps.part_id = p.part_id
        LEFT JOIN Traceability_TEST.dbo.c_station cs
            ON cs.station_id = ps.station_id
        LEFT JOIN Traceability_TEST.dbo.h_part_status h999
            ON h999.part_id = p.part_id
           AND h999.station_id = '999'
        ORDER BY p.part_id;
    """

    with pyodbc.connect(conn_str) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (input_value, input_value))
            rows = cursor.fetchall()

            if not rows:
                return None

            result = []
            for row in rows:
                result.append({
                    "part_id": row[0],
                    "source_shipping_id": row[1],
                    "last_status": row[2],
                    "status_timestamp": row[3],
                    "current_GiBo": row[4],
                    "current_station_id": row[5],
                    "current_station_name": row[6],
                    "melt": row[7],
                    "part_type": row[8],
                    "qc_forging_protocol": row[9],
                    "lab_forging_protocol": row[10]
                })
            return result


def process_request(input_value: str, conn_str: str) -> Tuple[Dict[str, Any], int]:
    """Process the request using a thread pool."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            parts_future = executor.submit(fetch_parts_by_shipping, conn_str, input_value)
            parts = parts_future.result()

        if parts:
            return {"parts": parts}, 200
        return {"message": "No records found for input value: " + input_value}, 200
    except Exception as e:
        logging.error(f"Error in process_request: {e}")
        return {"error": str(e)}, 500
