import json
import logging
import pyodbc
import azure.functions as func
from shared_utils import get_connection_string

logging.basicConfig(level=logging.INFO)

bp = func.Blueprint()


@bp.function_name(name="GetFurnaceReport")
@bp.route(route="FurnaceReport", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def furnace_report(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("FurnaceReport function processing a request")
    input_value = (
        req.params.get('value')
        or req.params.get('dmc')
        or req.params.get('part_id')
        or req.params.get('partId')
    )

    if not input_value:
        return func.HttpResponse(
            "Please pass value/dmc/part_id in the query string",
            status_code=400
        )

    db = req.params.get('db', 'prod')
    try:
        conn_str = get_connection_string()
        logging.info(f"FurnaceReport using db={db}")
    except Exception as e:
        logging.error(f"Error building connection string: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Database configuration error"}),
            status_code=500,
            mimetype="application/json"
        )

    try:
        db_name = "Traceability" if db == "prod" else "Traceability_TEST"
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                query = f"""
                    SELECT
                        [id],
                        [DMC],
                        [PartID],
                        [Furnace],
                        [MinTemp],
                        [MaxTemp],
                        [AvgTemp],
                        [MeasurementCount],
                        [InsertTime],
                        [FurnaceTimeSeconds],
                        [FurnaceTimeHours],
                        [TempStartTime],
                        [TempEndTime],
                        [TempDifference],
                        [MeasurementsPerMinute],
                        [created_timestamp],
                        [updated_timestamp]
                    FROM [{db_name}].[dbo].[furnace_temperature_report]
                    WHERE [DMC] = ? OR [PartID] = ?
                    ORDER BY [InsertTime] ASC
                """
                cursor.execute(query, (input_value, input_value))
                rows = cursor.fetchall()

        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "dmc": row[1],
                "part_id": row[2],
                "furnace": row[3],
                "min_temp": row[4],
                "max_temp": row[5],
                "avg_temp": row[6],
                "measurement_count": row[7],
                "insert_time": row[8],
                "furnace_time_seconds": row[9],
                "furnace_time_hours": row[10],
                "temp_start_time": row[11],
                "temp_end_time": row[12],
                "temp_difference": row[13],
                "measurements_per_minute": row[14],
                "created_timestamp": row[15],
                "updated_timestamp": row[16]
            })

        return func.HttpResponse(
            json.dumps({"rows": result}, default=str),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error processing furnace report: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
