import pulumi
import pulumi_aws as aws
from pathlib import Path
import json
from vpc import VpcComponent
from postgres_secret import PostgresSecret, PostgresSecretArgs
from rds_postgres import RdsPostgres, RdsPostgresArgs
from postgres_initializer import PostgresInitializer, PostgresInitializerArgs

# Configuration settings
config = pulumi.Config()
db_name = config.get("dbName") or "mydb"
db_username = config.get("dbUsername") or "admin"
db_password = config.require_secret("dbPassword")  # requires a secret value
db_instance_class = config.get("dbInstanceClass") or "db.t3.micro"
db_allocated_storage = config.get_int("dbAllocatedStorage") or 20  # in GB
db_backup_retention = config.get_int("dbBackupRetention") or 7  # in days

secret_name = "chinook/postgres"
sql_folder = f"{Path.home()}/workspace/data/postgres"
bucket_name = "rds-chinnook"

vpc = VpcComponent("rds-postgres", cidr_block="10.0.0.0/16")

rds_postgres = RdsPostgres(
    "rds-postgres",
    RdsPostgresArgs(
        vpc_id=vpc.vpc.id,
        public_subnet_ids=[vpc.public_subnet1.id, vpc.public_subnet2.id],
        db_instance_class=db_instance_class,
        db_allocated_storage=db_allocated_storage,
        db_name=db_name,
        db_username=db_username,
        db_password=db_password,
        db_backup_retention=db_backup_retention,
    ),
)

pulumi.export("rds_instance_endpoint", rds_postgres.rds_instance_endpoint)

postgres_secret = PostgresSecret(
    "postgres-secret",
    PostgresSecretArgs(
        secret_name=secret_name,
        db_name=db_name,
        db_username=db_username,
        db_password=db_password,
        instance_endpoint=rds_postgres.rds_instance_endpoint,
    ),
)

pulumi.export("secret_version_arn", postgres_secret.secret_version_arn)

initializer = PostgresInitializer(
    "postgres-initializer",
    PostgresInitializerArgs(
        sql_folder=sql_folder,
        bucket_name=bucket_name,
        rds_host=rds_postgres.rds_instance_endpoint,
        rds_port=5432,
        rds_username=db_username,
        rds_password=db_password,
        rds_db_name=db_name,
    ),
)

pulumi.export("bucket_name", initializer.bucket_name)
pulumi.export("lambda_function_arn", initializer.lambda_function_arn)
