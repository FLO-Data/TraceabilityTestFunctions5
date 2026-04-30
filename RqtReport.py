import json
import logging
import os

import azure.functions as func
import pymssql

logging.basicConfig(level=logging.INFO)

bp = func.Blueprint()


def _get_rockq_connection():
    server = os.environ["ROCKQ_DB_SERVER"]
    user = os.environ["ROCKQ_DB_USER"]
    password = os.environ["ROCKQ_DB_PASSWORD"]
    database = os.environ["ROCKQ_DB_NAME"]
    return pymssql.connect(server=server, user=user, password=password, database=database, login_timeout=15)


@bp.function_name(name="GetRqtReport")
@bp.route(route="RqtReport", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def rqt_report(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("RqtReport function processing a request")

    dpm = (
        req.params.get("dpm")
        or req.params.get("part_id")
        or req.params.get("value")
    )

    if not dpm:
        return func.HttpResponse(
            "Please pass dpm/part_id/value in the query string",
            status_code=400,
        )

    try:
        conn = _get_rockq_connection()
    except KeyError as e:
        logging.error(f"Missing environment variable: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Database configuration error"}),
            status_code=500,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"Error connecting to RockQ database: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Database connection failed"}),
            status_code=500,
            mimetype="application/json",
        )

    try:
        # One result row per (unique_trace_id, pos_workplace) — i.e. one row per
        # work-station the part actually visited (SW3-Laser, SW3-CNC, Quality
        # control, Packaging Kamenice, Relocation, ...). Laser fields are only
        # populated on the SW3-Laser row; for every other station they are NULL.
        query = """
            SELECT
                MAX(CASE WHEN v.header_attribute_id = 2131 THEN v.header_value_string END) AS dpm,
                v.pos_workplace                                                              AS station,
                MAX(CASE WHEN v.header_attribute_id = 2140 THEN v.header_value_string END) AS operator,
                MIN(v.header_creation_time)                                                  AS date_in,
                MAX(v.header_creation_time)                                                  AS date_out,
                CASE WHEN v.pos_workplace = 'SW3-Laser' THEN
                    COALESCE(
                        MAX(CASE WHEN v.header_attribute_id = 10001 THEN v.header_value_string END),
                        MAX(CASE WHEN v.header_attribute_id = 2132  THEN v.header_value_string END)
                    )
                END AS laser_data,
                CASE WHEN v.pos_workplace = 'SW3-Laser' THEN
                    COALESCE(
                        MAX(CASE WHEN v.header_attribute_id = 10101 THEN v.header_value_string END),
                        MAX(CASE WHEN v.header_attribute_id = 2134  THEN v.header_value_string END)
                    )
                END AS laser_quality
            FROM v_traceability_report v
            WHERE v.pos_workplace IS NOT NULL
            GROUP BY v.unique_trace_id, v.pos_workplace
            HAVING MAX(CASE WHEN v.header_attribute_id = 2131 THEN v.header_value_string END) = %s
            ORDER BY MIN(v.header_creation_time)
        """

        with conn:
            cursor = conn.cursor(as_dict=True)
            cursor.execute(query, (dpm,))
            rows = cursor.fetchall()

        result = [
            {
                "dpm": row["dpm"],
                "station": row["station"],
                "operator": row["operator"],
                "date_in": row["date_in"],
                "date_out": row["date_out"],
                "laser_data": row["laser_data"],
                "laser_quality": row["laser_quality"],
            }
            for row in rows
        ]

        return func.HttpResponse(
            json.dumps({"rows": result}, default=str),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"Error processing RQT report: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
