import os
import pathlib

import pulumi
import pulumi_aws as aws

from pulumi import ComponentResource, ResourceOptions
from api_maker.utils.logger import logger
from api_maker.cloudprints.python_archive_builder import PythonArchiveBuilder
from api_maker.cloudprints.pulumi.lambda_ import (
    PythonFunctionCloudprint,
    PythonFunctionCloudprintArgs,
)

log = logger(__name__)


class PostgresInitializerArgs:
    def __init__(
        self,
        *,
        secrets: dict[str, str],
        database: str,
        vpc_config=None,
        tags: dict[str, str] = None,
    ):
        self.secrets = secrets
        self.database = database
        self.vpc_config = vpc_config
        self.tags = tags


class PostgresInitializer(ComponentResource):
    def __init__(
        self, name: str, args: PostgresInitializerArgs, opts: ResourceOptions = None
    ):
        super().__init__("custom:resource:PostgresInitializer", name, {}, opts)

        log.info("postgres initializer")
        self.name = name
        self.args = args
        lambda_function = self.deploy_lambda()

        # Invoke the Lambda function
        lambda_invocation = aws.lambda_.Invocation(
            f"{name}-lambda-invocation",
            function_name=lambda_function.name,
            input="",
            opts=ResourceOptions(parent=lambda_function),
        )

    def deploy_lambda(self) -> aws.lambda_.Function:
        api_maker_source = "/Users/clydedanielrepik/workspace/api_maker/src/api_maker"

        self.archive_builder = PythonArchiveBuilder(
            name=f"{self.name}-archive-builder",
            sources={
                "api_maker": api_maker_source,
                "sql/chinook.sql": f"{pathlib.Path.home()}/workspace/api_maker/dev_playground/postgres/Chinook_Postgres.sql",
                "app.py": "initializer_handler.py",
            },
            requirements=[
                "psycopg2-binary",
            ],
            working_dir="temp",
        )

        log.debug("archive built")

        environment = {"SECRETS": self.args.secrets, "DATABASE": self.args.database}
        if os.environ.get("AWS_PROFILE") == "localstack":
            environment.update(
                {
                    "AWS_ACCESS_KEY_ID": "test",
                    "AWS_SECRET_ACCESS_KEY": "test",
                    "AWS_ENDPOINT_URL": "http://localstack:4566",
                }
            )

        lambda_function = PythonFunctionCloudprint(
            name=self.name,
            args=PythonFunctionCloudprintArgs(
                hash=self.archive_builder.hash(),
                handler="app.handler",
                archive_location=self.archive_builder.location(),
                environment=environment,
                timeout=60,
                tags=self.args.tags or {},
                vpc_config={
                    "vpc_id": "vpc-03d0b5f08f120f57c",
                    "security_group_ids": ["sg-07efca72d1041f9f3"],
                    "subnet_ids": [
                        "subnet-0deb799cdd3bc90d7",
                        "subnet-02b4eaee27ddd71c4",
                    ],
                },
            ),
        )

        return lambda_function.lambda_


"""
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
            assume_role_policy={
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
            },
            opts=ResourceOptions(parent=self),
        )

        lambda_policy = aws.iam.RolePolicy(
            f"{name}-lambda-policy",
            role=lambda_role.id,
            policy=bucket.arn.apply(
                lambda bucket_arn: f{{
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
                            "ec2:CreateNetworkInterface",
                            "ec2:DescribeNetworkInterfaces",
                            "ec2:DeleteNetworkInterface",
                        ],
                        "Resource": "*",
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
            }}
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
"""
