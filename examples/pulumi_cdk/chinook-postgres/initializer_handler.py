import logging
import os
import psycopg2

from pathlib import Path

from api_maker.connectors.connection_factory import ConnectionFactory

log = logging.getLogger(__name__)


def handler(event, _):
    # Retrieve the list of SQL files from the S3 bucket
    folder_path = Path("/var/task/sql")
    sql_files = [f for f in folder_path.iterdir() if f.is_file()]

    # Connect to the PostgreSQL database
    conn = ConnectionFactory().get_connection("chinook").get_connection()
    """
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "postgres_db"),
        port=os.environ.get("DB_PORT", 5432),
        user=os.environ.get("DB_USER", "chinook_user"),
        password=os.environ.get("DB_PASSWORD", "chinook_password"),
        dbname=os.environ.get("DB_NAME", "public")
    )
    """
    conn.autocommit = True
    cur = conn.cursor()

    # Execute each SQL file
    for sql_file in sql_files:
        log.info(f"Processing file: {sql_file}")

        try:
            sql_content = sql_file.read_text(encoding="utf-8")
            cur.execute(sql_content)
            log.info(f"Executed {sql_file} successfully")
        except Exception as e:
            log.error(f"Error executing {sql_file}: {e}")

    # Close the database connection
    cur.close()
    conn.close()

    return {"statusCode": 200, "body": "SQL scripts executed successfully"}
