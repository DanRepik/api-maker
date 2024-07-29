import json
import pulumi
import pulumi_aws as aws
from typing import Dict, Optional

from api_maker.utils.logger import logger

log = logger(__name__)


class PythonFunctionCloudprintArgs:
    def __init__(
        self,
        hash: str,
        archive_location: str,
        handler: str,
        environment: Optional[Dict[str, str]] = None,
        memory_size: int = 128,
        reserved_concurrent_executions: int = -1,
        timeout: int = 3,
        tags: Optional[Dict[str, str]] = None,
        vpc_config: Optional[Dict[str, pulumi.Input]] = None,
    ):
        self.hash = hash
        self.archive_location = archive_location
        self.handler = handler
        self.environment = environment or {}
        self.memory_size = memory_size
        self.reserved_concurrent_executions = reserved_concurrent_executions
        self.timeout = timeout
        self.tags = tags
        self.vpc_config = vpc_config


class PythonFunctionCloudprint(pulumi.ComponentResource):
    name: str
    handler: str
    lambda_: aws.lambda_.Function

    def __init__(
        self,
        name: str,
        args: PythonFunctionCloudprintArgs,
        opts: pulumi.ResourceOptions = None,
    ):
        super().__init__("custom:resource:PythonFunctionCloudprint", name, {}, opts)
        self.name = name
        self.args = args
        self.create_lambda_function()
        self.register_outputs({})

    def create_execution_role(self) -> aws.iam.Role:
        log.info(f"{self.name} creating execution role")
        assume_role_policy = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    effect="Allow",
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="Service",
                            identifiers=["lambda.amazonaws.com"],
                        )
                    ],
                    actions=["sts:AssumeRole"],
                )
            ]
        )

        role = aws.iam.Role(
            f"{self.name}-lambda-execution",
            assume_role_policy=assume_role_policy.json,
            tags=self.args.tags,
        )
        log.info(f"{self.name} creating execution role 1")

        aws.iam.RolePolicy(
            f"{self.name}-lambda-policy",
            role=role.id,
            policy=pulumi.Output.all(role.arn).apply(
                lambda arn: json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents",
                                ],
                                "Resource": "arn:aws:logs:*:*:*",
                            },
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "ec2:CreateNetworkInterface",
                                    "ec2:DescribeNetworkInterfaces",
                                    "ec2:DeleteNetworkInterface",
                                ],
                                "Resource": "*",
                            },
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "secretsmanager:GetSecretValue",
                                    "secretsmanager:DescribeSecret",
                                ],
                                "Resource": "arn:aws:secretsmanager:*:*:secret:*",
                            },
                        ],
                    }
                )
            ),
        )
        log.info(f"{self.name} creating execution role policy")

        return role

    def create_log_group(self) -> aws.cloudwatch.LogGroup:
        log.info(f"{self.name} creating log group")
        log_group = aws.cloudwatch.LogGroup(
            f"{self.name}-log-group",
            name=f"/aws/lambda/{pulumi.get_project()}-{self.name}",
            retention_in_days=3,
            tags=self.args.tags,
        )
        return log_group

    @property
    def invoke_arn(self) -> pulumi.Output[str]:
        return self.lambda_.invoke_arn

    def create_lambda_function(self):
        log.info(f"{self.name} creating lambda function")

        log_group = self.create_log_group()
        execution_role = self.create_execution_role()
        log.info(f"{self.name} creating role done")

        if self.args.vpc_config:
            log.info(f"{self.name} creating lambda vpc")
            lambda_security_group = aws.ec2.SecurityGroup(
                f"{self.name}-lambda-sg",
                vpc_id=self.args.vpc_config["vpc_id"],
                description="Allow Lambda to access the internet",
                ingress=[
                    {
                        "protocol": "-1",
                        "from_port": 0,
                        "to_port": 0,
                        "cidr_blocks": ["0.0.0.0/0"],
                    }
                ],
                egress=[
                    {
                        "protocol": "-1",  # Allow all outbound traffic
                        "from_port": 0,
                        "to_port": 0,
                        "cidr_blocks": ["0.0.0.0/0"],
                    }
                ],
            )

            self.lambda_ = aws.lambda_.Function(
                f"{self.name}-lambda",
                code=pulumi.FileArchive(self.args.archive_location),
                name=self.name,
                role=execution_role.arn,
                handler=self.args.handler,
                memory_size=self.args.memory_size,
                reserved_concurrent_executions=self.args.reserved_concurrent_executions,
                timeout=self.args.timeout,
                vpc_config=aws.lambda_.FunctionVpcConfigArgs(
                    subnet_ids=self.args.vpc_config["subnet_ids"],
                    security_group_ids=self.args.vpc_config["security_group_ids"],
                ),
                source_code_hash=self.args.hash,
                runtime=aws.lambda_.Runtime.PYTHON3D9,
                environment=aws.lambda_.FunctionEnvironmentArgs(
                    variables=self.args.environment
                ),
                opts=pulumi.ResourceOptions(depends_on=[execution_role, log_group]),
                tags=self.args.tags,
            )
        else:
            self.lambda_ = aws.lambda_.Function(
                f"{self.name}-lambda",
                code=pulumi.FileArchive(self.args.archive_location),
                name=self.name,
                role=execution_role.arn,
                handler=self.args.handler,
                memory_size=self.args.memory_size,
                reserved_concurrent_executions=self.args.reserved_concurrent_executions,
                timeout=self.args.timeout,
                source_code_hash=self.args.hash,
                runtime=aws.lambda_.Runtime.PYTHON3D9,
                environment=aws.lambda_.FunctionEnvironmentArgs(
                    variables=self.args.environment
                ),
                opts=pulumi.ResourceOptions(depends_on=[log_group]),
                tags=self.args.tags,
            )
