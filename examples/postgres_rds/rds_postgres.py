import pulumi
import pulumi_aws as aws
from pulumi import ComponentResource, ResourceOptions, Output
from typing import List


class RdsPostgresArgs:
    def __init__(
        self,
        vpc_id: str,
        public_subnet_ids: List[str],
        db_instance_class: str,
        db_allocated_storage: int,
        db_name: str,
        db_username: str,
        db_password: str,
        db_backup_retention: int,
    ):
        self.vpc_id = vpc_id
        self.public_subnet_ids = public_subnet_ids
        self.db_instance_class = db_instance_class
        self.db_allocated_storage = db_allocated_storage
        self.db_name = db_name
        self.db_username = db_username
        self.db_password = db_password
        self.db_backup_retention = db_backup_retention


class RdsPostgres(ComponentResource):
    def __init__(self, name: str, args: RdsPostgresArgs, opts: ResourceOptions = None):
        super().__init__("custom:resource:RdsPostgres", name, {}, opts)

        # Security group for RDS
        rds_security_group = aws.ec2.SecurityGroup(
            f"{name}-rds-security-group",
            vpc_id=args.vpc_id,
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
                {
                    "protocol": "-1",
                    "from_port": 0,
                    "to_port": 0,
                    "cidr_blocks": ["0.0.0.0/0"],
                }
            ],
            opts=ResourceOptions(parent=self),
        )

        # Subnet group for RDS
        rds_subnet_group = aws.rds.SubnetGroup(
            f"{name}-rds-subnet-group",
            subnet_ids=args.public_subnet_ids,
            opts=ResourceOptions(parent=self),
        )

        # Create the RDS PostgreSQL instance
        rds_instance = aws.rds.Instance(
            f"{name}-postgres-rds-instance",
            instance_class=args.db_instance_class,
            allocated_storage=args.db_allocated_storage,
            engine="postgres",
            engine_version="16.3",
            db_name=args.db_name,
            username=args.db_username,
            password=args.db_password,
            backup_retention_period=args.db_backup_retention,
            skip_final_snapshot=True,
            vpc_security_group_ids=[rds_security_group.id],
            db_subnet_group_name=rds_subnet_group.name,
            tags={"Name": f"{name}-postgres-rds-instance"},
            opts=ResourceOptions(parent=self),
        )

        self.rds_security_group_id = rds_security_group.id
        self.rds_instance_endpoint = rds_instance.endpoint

        self.register_outputs(
            {
                "rds_security_group_id": self.rds_security_group_id,
                "rds_instance_endpoint": self.rds_instance_endpoint,
            }
        )
