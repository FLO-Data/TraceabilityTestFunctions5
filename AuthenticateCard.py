"""
Azure Function for NFC/RFID Card Authentication
Autentifikácia používateľov pomocou NFC/RFID kariet
"""

import logging
import azure.functions as func
import pyodbc
import json
import os
from typing import Optional, Dict, Any

# Create a Blueprint for registering with the Functions host
bp = func.Blueprint()

def get_connection_string() -> str:
    """Get the database connection string from environment variables."""
    sql_conn_str = os.getenv("AZURE_SQL_CONNECTION_STRING")
    sql_user = os.getenv("AZURE_SQL_DB_USER")
    sql_pwd = os.getenv("AZURE_SQL_DB_PASSWORD")
    sql_driver = os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 17 for SQL Server")

    return (f"Driver={sql_driver};"
            f"Server={sql_conn_str};"
            "Database=Traceability_TEST;"
            f"Uid={sql_user};"
            f"Pwd={sql_pwd};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=60;")

def authenticate_card(conn_str: str, card_id: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user by NFC/RFID card ID
    Autentifikácia používateľa podľa ID NFC/RFID karty
    
    Args:
        conn_str: Database connection string
        card_id: NFC/RFID card ID
        
    Returns:
        Dictionary with authentication result or None on error
    """
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Call stored procedure
        cursor.execute("EXEC [dbo].[sp_authenticate_card] ?", (card_id,))
        
        # Get result
        row = cursor.fetchone()
        
        if row:
            result = {
                'status': row[0],
                'message': row[1],
                'employee_name': row[2],
                'employee_id': row[3]
            }
        else:
            result = {
                'status': 'error',
                'message': 'No result from database',
                'employee_name': None,
                'employee_id': None
            }
        
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        logging.error(f"Error authenticating card {card_id}: {str(e)}")
        return {
            'status': 'error',
            'message': f'Database error: {str(e)}',
            'employee_name': None,
            'employee_id': None
        }

@bp.route(route="authenticatecard", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def AuthenticateCard(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint for NFC/RFID card authentication
    HTTP endpoint pre autentifikáciu NFC/RFID karty
    
    GET/POST Parameters:
        - card_id: NFC/RFID card ID (required)
        
    Returns:
        JSON response with authentication result
    """
    logging.info('AuthenticateCard function processed a request.')
    
    try:
        # Get card_id from request
        if req.method == "GET":
            card_id = req.params.get('card_id')
        else:
            try:
                req_body = req.get_json()
                card_id = req_body.get('card_id') if req_body else None
            except ValueError:
                card_id = None
        
        # Validate card_id
        if not card_id:
            return func.HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'Missing required parameter: card_id',
                    'employee_name': None,
                    'employee_id': None
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get connection string
        conn_str = get_connection_string()
        
        # Authenticate card
        result = authenticate_card(conn_str, card_id)
        
        if not result:
            return func.HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'Internal server error',
                    'employee_name': None,
                    'employee_id': None
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        # Return result
        status_code = 200 if result['status'] == 'success' else 401
        
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in AuthenticateCard: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                'status': 'error',
                'message': f'Internal server error: {str(e)}',
                'employee_name': None,
                'employee_id': None
            }),
            status_code=500,
            mimetype="application/json"
        )

