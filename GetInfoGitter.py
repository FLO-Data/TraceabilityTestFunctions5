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

@bp.function_name(name="GetInfoGitter")
@bp.route(route="GetInfoGitter", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def GetInfoGitter(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("GetInfoGitter function processing a request")
    shipping_id = req.params.get('shipping_id')
    
    if not shipping_id:
        try:
            req_body = req.get_json()
            logging.info(f"Attempting to get shipping_id from request body: {req_body}")
        except ValueError:
            logging.warning("No JSON body in request")
            pass
        else:
            shipping_id = req_body.get('shipping_id')
            
    if not shipping_id:
        logging.error("No shipping_id provided in request")
        return func.HttpResponse(
            json.dumps({"error": "Please pass shipping_id in the query string or request body"}),
            status_code=400,
            mimetype="application/json"
        )

    logging.info(f"Processing request for shipping_id: {shipping_id}")
    
    # Get the connection string from environment variables
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
        # Process request with concurrent database operations
        logging.info("Starting database query")
        response_data, status_code = process_request(shipping_id, conn_str)
        logging.info(f"Query completed with status code: {status_code}")
        
        if status_code != 200:
            return func.HttpResponse(
                json.dumps(response_data),
                status_code=status_code,
                mimetype="application/json"
            )
            
        response = json.dumps(response_data, default=str)
        logging.info("Successfully processed request")
        
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

def fetch_gitter_parts(conn_str: str, shipping_id: str) -> Optional[List[Dict[str, Any]]]:
    """Get all parts in the specified gitterbox (shipping_id)."""
    with pyodbc.connect(conn_str) as conn:
        with conn.cursor() as cursor:
            # Query to get all parts in the gitterbox from part_status
            gitter_query = """
                SELECT 
                    ps.part_id,
                    ps.last_status,
                    ps.station_id,
                    ps.status_timestamp,
                    ps.create_timestamp,
                    ps.employee_id,
                    ps.shipping_id,
                    cst.station_name
                FROM dbo.part_status ps
                LEFT JOIN dbo.c_station cst ON cst.station_id = ps.station_id
                WHERE ps.shipping_id = ?
                ORDER BY ps.status_timestamp DESC
            """
            cursor.execute(gitter_query, (shipping_id,))
            rows = cursor.fetchall()
            
            if not rows:
                return None
            
            # Convert the results to a list of dictionaries
            # Match production format exactly (no station_name)
            result = []
            for row in rows:
                result.append({
                    'part_id': row[0],
                    'create_timestamp': row[4],
                    'employee_id': row[5],
                    'station_id': row[2],
                    'last_status': row[1],
                    'status_timestamp': row[3],
                    'shipping_id': row[6]
                })
            
            return result

def process_request(shipping_id: str, conn_str: str) -> Tuple[Dict[str, Any], int]:
    """Process the request with concurrent database operations using thread pool."""
    try:
        # Run database operation
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            gitter_parts_future = executor.submit(fetch_gitter_parts, conn_str, shipping_id)
            
            # Get result
            gitter_parts = gitter_parts_future.result()
            
            # Create response data structure (match production format exactly)
            if gitter_parts:
                response_data = {
                    'gitter_history': gitter_parts
                }
            else:
                response_data = {
                    'gitter_history': []
                }
                
            return response_data, 200
    except Exception as e:
        logging.error(f"Error in process_request: {e}")
        return {"error": str(e)}, 500

