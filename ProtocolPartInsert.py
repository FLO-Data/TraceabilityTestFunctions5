import logging
import azure.functions as func
import pyodbc
import json
import asyncio
import concurrent.futures
from typing import Dict, Any
from shared_utils import get_connection_string

# Create a Blueprint for registering with the Functions host
bp = func.Blueprint()

async def insert_protocol_part(data: Dict[str, Any], conn_str: str) -> None:
    """Insert protocol part data into database using a separate thread."""
    part_id = data.get("part_id")
    employee_id = data.get("employee_id")
    station_id = data.get("station_id")
    status = data.get("status")
    status_timestamp = data.get("status_timestamp")
    shipping_id = data.get("shipping_id")
    protocol_id = data.get("protocol_id")
    
    # Use thread pool for database operations
    with concurrent.futures.ThreadPoolExecutor() as pool:
        await asyncio.get_event_loop().run_in_executor(
            pool,
            execute_stored_procedure,
            conn_str,
            part_id,
            employee_id,
            station_id,
            status,
            status_timestamp,
            shipping_id,
            protocol_id
        )

def execute_stored_procedure(conn_str: str, part_id: str, employee_id: str, station_id: str, 
                            status: str, status_timestamp: str, shipping_id: str = None, 
                            protocol_id: str = None) -> None:
    """Execute the stored procedure with detailed logging."""
    logging.info(f"Attempting to execute stored procedure 'insert_protocol_part' for part_id: {part_id}")
    try:
        with pyodbc.connect(conn_str, timeout=30) as conn:
            logging.info(f"DB connection successful for part_id: {part_id}.")
            cursor = conn.cursor()
            
            logging.info(f"Executing stored procedure with params: part_id={part_id}, protocol_id={protocol_id}, status={status}")
            cursor.execute(
                "{CALL insert_protocol_part (?, ?, ?, ?, ?, ?, ?)}",
                part_id,
                employee_id,
                station_id,
                status,
                status_timestamp,
                shipping_id,
                protocol_id
            )
            conn.commit()
            logging.info(f"Stored procedure executed and committed successfully for part_id: {part_id}")

    except pyodbc.Error as db_error:
        logging.error(f"DATABASE ERROR executing stored procedure for part_id {part_id}: {db_error}", exc_info=True)
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred in execute_stored_procedure for part_id {part_id}: {e}", exc_info=True)
        raise

@bp.function_name(name="ProtocolPartInsertHttpFunc")
@bp.route(route="ProtocolPartInsert", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def http_function(req: func.HttpRequest) -> func.HttpResponse:
    """Process HTTP request to insert protocol part data with detailed logging."""
    logging.info("ProtocolPartInsert Azure function triggered.")
    
    try:
        # Zkontroluj, zda je request JSON
        if not req.headers.get('content-type', '').startswith('application/json'):
            logging.error("Invalid content-type. Expected application/json")
            return func.HttpResponse(
                body=json.dumps({"error": "Content-Type must be application/json"}),
                mimetype="application/json",
                status_code=400
            )
        
        req_body = req.get_json()
        logging.info(f"Received request body: {req_body}")
        
        part_id = req_body.get("part_id")
        protocol_id = req_body.get("protocol_id")
        if not part_id or not protocol_id:
            logging.error(f"Invalid request body. Missing part_id or protocol_id. Payload: {req_body}")
            return func.HttpResponse(
                body=json.dumps({"error": "Request body must contain 'part_id' and 'protocol_id'"}),
                mimetype="application/json",
                status_code=400
            )

        conn_str = get_connection_string()

        # Process request using the same async function as queue
        await insert_protocol_part(req_body, conn_str)
        
        logging.info(f"Successfully processed request for part_id: {part_id}, protocol_id: {protocol_id}")
        return func.HttpResponse(
            body=json.dumps({"message": "Protocol part data inserted successfully"}),
            mimetype="application/json",
            status_code=200
        )
        
    except ValueError as ve:
        # Catches JSON decoding errors or errors from get_connection_string
        logging.error(f"ValueError processing request: {ve}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": str(ve)}),
            mimetype="application/json",
            status_code=400
        )
    except pyodbc.Error as db_error:
        logging.error(f"Database error in ProtocolPartInsert: {db_error}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "Database connection error. Check logs for details."}),
            mimetype="application/json",
            status_code=500
        )
    except Exception as e:
        logging.error(f"An unhandled exception occurred in ProtocolPartInsert: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "An internal server error occurred. Check logs for details."}),
            mimetype="application/json",
            status_code=500
        )

@bp.function_name(name="ProtocolPartInsertQueueFunc")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="protocol-part-insert-test",
    connection="AzureWebJobsStorage"
)
async def queue_function(msg: func.QueueMessage) -> None:
    """Process queue message for protocol part insert."""
    conn_str = get_connection_string()
    
    try:
        # Decode and parse the queue message
        message_body = msg.get_body().decode("utf-8")
        logging.info(f"Processing protocol part queue message: {message_body}")
        
        data = json.loads(message_body)
        
        # Validate required fields
        part_id = data.get("part_id")
        protocol_id = data.get("protocol_id")
        if not part_id or not protocol_id:
            logging.error(f"Invalid queue message. Missing part_id or protocol_id. Data: {data}")
            raise ValueError("Queue message must contain 'part_id' and 'protocol_id'")
        
        # Process message asynchronously
        await insert_protocol_part(data, conn_str)
        logging.info(f"Successfully processed protocol part queue message for part_id: {part_id}, protocol_id: {protocol_id}")
        
    except json.JSONDecodeError as e:
        logging.error(f"Invalid message format. Expected JSON. Error: {e}")
        raise
    except ValueError as ve:
        logging.error(f"Validation error in queue message: {ve}")
        raise
    except Exception as e:
        logging.error(f"Error processing protocol part queue message: {e}")
        raise