import os

import pulumi
import pulumi_aws as aws

from pulumi import ComponentResource, ResourceOptions
from api_maker.cloudprints.python_archive_builder import PythonArchiveBuilder

handler = """
import os
import boto3
import psycopg2

def handler(event, context):
    # Initialize S3 client
    s3_client = boto3.client('s3')

    # Retrieve the list of SQL files from the S3 bucket
    response = s3_client.list_objects_v2(Bucket=os.getenv('BUCKET_NAME'))
    sql_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.sql')]

    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        host=os.getenv('RDS_HOST'),
        port=os.getenv('RDS_PORT', 5432),
        user=os.getenv('RDS_USER'),
        password=os.getenv('RDS_PASSWORD'),
        dbname=os.getenv('RDS_DB_NAME')
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Execute each SQL file
    for sql_file in sql_files:
        print(f"Processing file: {sql_file}")
        obj = s3_client.get_object(Bucket=os.getenv('BUCKET_NAME'), Key=sql_file)
        sql_content = obj['Body'].read().decode('utf-8')

        try:
            cur.execute(sql_content)
            print(f"Executed {sql_file} successfully")
        except Exception as e:
            print(f"Error executing {sql_file}: {e}")

    # Close the database connection
    cur.close()
    conn.close()

    return {
        'statusCode': 200,
        'body': 'SQL scripts executed successfully'
    }
"""


class PostgresInitializerArgs:
    def __init__(
        self,
        sql_folder: str,
        bucket_name: str,
        rds_host: str,
        rds_port: int,
        rds_username: str,
        rds_password: str,
        rds_db_name: str,
    ):
        self.sql_folder = sql_folder
        self.bucket_name = bucket_name
        self.rds_host = rds_host
        self.rds_port = rds_port
        self.rds_username = rds_username
        self.rds_password = rds_password
        self.rds_db_name = rds_db_name


class PostgresInitializer(ComponentResource):
    def __init__(
        self, name: str, args: PostgresInitializerArgs, opts: ResourceOptions = None
    ):
        super().__init__("custom:resource:PostgresInitializer", name, {}, opts)

        # Create an S3 bucket
        bucket = aws.s3.Bucket(args.bucket_name, opts=ResourceOptions(parent=self))

        # Upload SQL files to the S3 bucket
        sql_files = []
        for file_name in os.listdir(args.sql_folder):
            if file_name.endswith(".sql"):
                file_path = os.path.join(args.sql_folder, file_name)
                s3_object = aws.s3.BucketObject(
                    file_name,
                    bucket=bucket,
                    source=pulumi.FileAsset(file_path),
                    opts=ResourceOptions(parent=bucket),
                )
                sql_files.append(s3_object)

        # Create a Lambda role
        lambda_role = aws.iam.Role(
            f"{name}-lambda-role",
            assume_role_policy="""{
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Effect": "Allow",
                        "Sid": ""
                    }
                ]
            }""",
            opts=ResourceOptions(parent=self),
        )

        lambda_policy = aws.iam.RolePolicy(
            f"{name}-lambda-policy",
            role=lambda_role.id,
            policy=bucket.arn.apply(
                lambda bucket_arn: f"""{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                        ],
                        "Resource": "arn:aws:logs:*:*:*",
                    }},
                    {{
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject"
                        ],
                        "Resource": "{bucket_arn}/*"
                    }},
                    {{
                        "Effect": "Allow",
                        "Action": [
                            "rds-db:connect"
                        ],
                        "Resource": "*"
                    }}
                ]
            }}"""
            ),
            opts=ResourceOptions(parent=lambda_role),
        )

        archive_builder = PythonArchiveBuilder(
            name=f"{name}-archive-builder",
            sources={"app.py": handler},
            requirements=[
                "psycopg2-binary",
            ],
            working_dir="temp",
        )

        # Create the Lambda function
        lambda_function = aws.lambda_.Function(
            f"{name}-lambda",
            runtime="python3.9",
            code=pulumi.FileArchive(archive_builder.location()),
            handler="app.handler",
            role=lambda_role.arn,
            environment={
                "variables": {
                    "RDS_HOST": args.rds_host,
                    "RDS_PORT": str(args.rds_port),
                    "RDS_USER": args.rds_username,
                    "RDS_PASSWORD": args.rds_password,
                    "RDS_DB_NAME": args.rds_db_name,
                    "BUCKET_NAME": bucket.id,
                }
            },
            opts=ResourceOptions(parent=self),
        )

        # Create a Lambda permission to allow S3 to invoke the Lambda function
        lambda_permission = aws.lambda_.Permission(
            f"{name}-lambda-permission",
            action="lambda:InvokeFunction",
            function=lambda_function.arn,
            principal="s3.amazonaws.com",
            source_arn=bucket.arn,
            opts=ResourceOptions(parent=lambda_function),
        )

        # Invoke the Lambda function
        lambda_invocation = aws.lambda_.Invocation(
            f"{name}-lambda-invocation",
            function_name=lambda_function.name,
            input="",
            opts=ResourceOptions(parent=lambda_function),
        )

        self.bucket_name = bucket.id
        self.lambda_function_arn = lambda_function.arn

        self.register_outputs(
            {
                "bucket_name": self.bucket_name,
                "lambda_function_arn": self.lambda_function_arn,
            }
        )
