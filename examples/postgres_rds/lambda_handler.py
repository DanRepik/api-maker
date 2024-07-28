import os
import boto3
import psycopg2


def handler(event, context):
    # Initialize S3 client
    s3_client = boto3.client("s3")

    # Retrieve the list of SQL files from the S3 bucket
    response = s3_client.list_objects_v2(Bucket=os.getenv("BUCKET_NAME"))
    sql_files = [
        obj["Key"]
        for obj in response.get("Contents", [])
        if obj["Key"].endswith(".sql")
    ]

    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        host=os.getenv("RDS_HOST"),
        port=os.getenv("RDS_PORT", 5432),
        user=os.getenv("RDS_USER"),
        password=os.getenv("RDS_PASSWORD"),
        dbname=os.getenv("RDS_DB_NAME"),
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Execute each SQL file
    for sql_file in sql_files:
        print(f"Processing file: {sql_file}")
        obj = s3_client.get_object(Bucket=os.getenv("BUCKET_NAME"), Key=sql_file)
        sql_content = obj["Body"].read().decode("utf-8")

        try:
            cur.execute(sql_content)
            print(f"Executed {sql_file} successfully")
        except Exception as e:
            print(f"Error executing {sql_file}: {e}")

    # Close the database connection
    cur.close()
    conn.close()

    return {"statusCode": 200, "body": "SQL scripts executed successfully"}
