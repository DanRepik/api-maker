import json
import pulumi
import pulumi_aws as aws
from pulumi import ComponentResource, ResourceOptions, Output, Input
from typing import List


class PostgresSecretArgs:
    def __init__(
        self,
        secret_name: str,
        db_name: str,
        db_username: str,
        db_password: str,
        instance_endpoint: Input[str],
    ):
        self.secret_name = secret_name
        self.db_name = db_name
        self.db_username = db_username
        self.db_password = db_password
        self.instance_endpoint = instance_endpoint


class PostgresSecret(ComponentResource):
    def __init__(
        self, name: str, args: PostgresSecretArgs, opts: ResourceOptions = None
    ):
        super().__init__("custom:resource:PostgresSecret", name, {}, opts)

        # Create the secret in AWS Secrets Manager
        # secret = aws.secretsmanager.Secret(args.secret_name, opts=ResourceOptions(parent=self))
        secret = aws.secretsmanager.get_secret(name=args.secret_name)

        # Wait for the RDS instance to be available and then create the secret version with the endpoint as the host
        def create_secret_version(
            secret_id, instance_endpoint, db_username, db_password, db_name, secret_name
        ):
            secret_value = json.dumps(
                {
                    "engine": "postgres",
                    "dbname": db_name,
                    "username": db_username,
                    "password": db_password,
                    "host": instance_endpoint,
                }
            )

            secret_version = aws.secretsmanager.SecretVersion(
                f"{secret_name}-version",
                secret_id=secret_id,
                secret_string=secret_value,
                opts=ResourceOptions(parent=self),
            )
            return secret_version.arn

        # Create the secret version
        self.secret_version_arn = Output.all(
            secret.id,
            args.instance_endpoint,
            args.db_username,
            args.db_password,
            args.db_name,
            args.secret_name,
        ).apply(lambda values: create_secret_version(*values))

        self.register_outputs({"secret_version_arn": self.secret_version_arn})
