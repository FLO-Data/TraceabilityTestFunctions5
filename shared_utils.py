import os

def get_connection_string() -> str:
    """Get the database connection string from environment variables."""
    sql_conn_str = os.getenv("AZURE_SQL_CONNECTION_STRING")
    sql_user = os.getenv("AZURE_SQL_DB_USER")
    sql_pwd = os.getenv("AZURE_SQL_DB_PASSWORD")
    sql_driver = os.getenv("AZURE_SQL_DRIVER")

    return (f"Driver={sql_driver};"
            f"Server={sql_conn_str};"
            "Database=Traceability_TEST;"
            f"Uid={sql_user};"
            f"Pwd={sql_pwd};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=60;")


