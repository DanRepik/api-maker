import pulumi
import pulumi_aws as aws
import json
from vpc import VpcComponent

# Configuration settings
config = pulumi.Config()
db_name = config.get("dbName") or "mydb"
db_username = config.get("dbUsername") or "admin"
db_password = config.require_secret("dbPassword")  # requires a secret value
db_instance_class = config.get("dbInstanceClass") or "db.t3.micro"
db_allocated_storage = config.get_int("dbAllocatedStorage") or 20  # in GB
db_backup_retention = config.get_int("dbBackupRetention") or 7  # in days

# Example usage
vpc = VpcComponent("rds-postgres", cidr_block="10.0.0.0/16")

pulumi.export("vpc_id", vpc.vpc.id)
pulumi.export("public_subnet_id1", vpc.public_subnet1.id)
pulumi.export("public_subnet_id2", vpc.public_subnet2.id)
pulumi.export("private_subnet_id1", vpc.private_subnet1.id)
pulumi.export("private_subnet_id2", vpc.private_subnet2.id)

# Security group for RDS
rds_security_group = aws.ec2.SecurityGroup(
    "rds-security-group",
    vpc_id=vpc.vpc.id,
    description="Allow access to RDS",
    ingress=[
        {
            "protocol": "tcp",
            "from_port": 5432,
            "to_port": 5432,
            "cidr_blocks": ["0.0.0.0/0"],
        }
    ],
    egress=[
        {"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}
    ],
)

# Create the RDS PostgreSQL instance
"""
rds_instance = aws.rds.Instance(
    "postgres-rds-instance",
    instance_class=db_instance_class,
    allocated_storage=db_allocated_storage,
    engine="postgres",
    engine_version="16.3",
    db_name=db_name,
    username=db_username,
    password=db_password,
    backup_retention_period=db_backup_retention,
    skip_final_snapshot=True,
    vpc_security_group_ids=[rds_security_group.id],
    db_subnet_group_name=aws.rds.SubnetGroup(
        "rds-subnet-group", subnet_ids=[vpc.public_subnet1.id, vpc.public_subnet2.id]
    ).name,
    tags={"Name": "postgres-rds-instance"},
)
"""
# Define the secret name
secret_name = "chinook/postgres"

# Create the secret in AWS Secrets Manager
secret = aws.secretsmanager.get_secret(name=secret_name)
# Secret(
#    secret_name,
#    name=secret_name,
#    description="Postgres database connection secret for Chinook",
# )


# Wait for the RDS instance to be available and then create the
# secret version with the endpoint as the host
def create_secret_version(args):
    secret_id, instance_endpoint, db_username, db_password = args
    secret_value = json.dumps(
        {
            "engine": "postgres",
            "dbname": "chinook_auto_increment",
            "username": db_username,
            "password": db_password,
            "host": instance_endpoint,
        }
    )

    secret_version = aws.secretsmanager.SecretVersion(
        f"{secret_name}-version",
        secret_id=secret_id,
        secret_string=secret_value,
    )
    return secret_version.arn


secret_version_arn = pulumi.Output.all(
    secret.id, "rds_instance.endpoint", db_username, db_password.apply(lambda pwd: pwd)
).apply(create_secret_version)

# Export the ARN of the created secret version
pulumi.export("secret_version_arn", secret_version_arn)

pulumi.export("rds_security_group", rds_security_group.id)
# pulumi.export("rds_instance_endpoint", rds_instance.endpoint)
