import os


def get_connection_string() -> str:
    """Get the database connection string from environment variables.

    Both `Traceability` (production) and `Traceability_TEST` databases live on the
    same SQL server, so a single connection is sufficient for read-only queries
    against either database — callers only need to qualify table references with
    a three-part name (e.g. `Traceability.dbo.traceability_log`).
    """
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


