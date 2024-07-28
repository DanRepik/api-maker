import json
import pulumi
import pulumi_aws as aws

from api_maker.utils.logger import logger

log = logger(__name__)


class PythonFunctionCloudprint(pulumi.ComponentResource):
    name: str
    handler: str
    lambda_: aws.lambda_.Function

    def __init__(
        self,
        name: str,
        hash: str,
        archive_location: str,
        handler: str,
        environment: dict = None,
        memory_size: int = 128,
        reserved_concurrent_executions: int = -1,
        timeout: int = 3,
        tags: dict = None,
        vpc_config: dict = None,
        opts: pulumi.ResourceOptions = None,
    ):
        super().__init__("custom:resource:PythonFunctionCloudprint", name, {}, opts)
        self.name = name
        self.handler = handler
        self.environment = environment or {}
        self.memory_size = memory_size
        self.reserved_concurrent_executions = reserved_concurrent_executions
        self.timeout = timeout
        self.tags = tags
        self.vpc_config = vpc_config
        self.create_lambda_function(hash, archive_location)
        self.register_outputs({})

    def create_execution_role(self) -> aws.iam.Role:
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
            tags=self.tags,
        )

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

        return role

    def create_log_group(self) -> aws.cloudwatch.LogGroup:
        log_group = aws.cloudwatch.LogGroup(
            f"{self.name}-log-group",
            name=f"/aws/lambda/{pulumi.get_project()}-{self.name}",
            retention_in_days=3,
            tags=self.tags,
        )
        return log_group

    @property
    def invoke_arn(self) -> pulumi.Output[str]:
        return self.lambda_.invoke_arn

    def create_lambda_function(self, hash: str, archive_location: str):
        log.debug("Creating lambda function")

        log_group = self.create_log_group()
        execution_role = self.create_execution_role()

        if self.vpc_config:
            lambda_security_group = aws.ec2.SecurityGroup(
                f"{self.name}-lambda-sg",
                vpc_id=self.vpc_config["vpc_id"],
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
                code=pulumi.FileArchive(archive_location),
                name=self.name,
                role=execution_role.arn,
                handler=self.handler,
                memory_size=self.memory_size,
                reserved_concurrent_executions=self.reserved_concurrent_executions,
                timeout=self.timeout,
                vpc_config=aws.lambda_.FunctionVpcConfigArgs(
                    subnet_ids=self.vpc_config["subnet_ids"],
                    security_group_ids=[lambda_security_group.id],
                ),
                source_code_hash=hash,
                runtime=aws.lambda_.Runtime.PYTHON3D9,
                environment=aws.lambda_.FunctionEnvironmentArgs(
                    variables=self.environment
                ),
                opts=pulumi.ResourceOptions(depends_on=[execution_role, log_group]),
                tags=self.tags,
            )
        else:
            self.lambda_ = aws.lambda_.Function(
                f"{self.name}-lambda",
                code=pulumi.FileArchive(archive_location),
                name=self.name,
                role=execution_role.arn,
                handler=self.handler,
                memory_size=self.memory_size,
                reserved_concurrent_executions=self.reserved_concurrent_executions,
                timeout=self.timeout,
                source_code_hash=hash,
                runtime=aws.lambda_.Runtime.PYTHON3D9,
                environment=aws.lambda_.FunctionEnvironmentArgs(
                    variables=self.environment
                ),
                opts=pulumi.ResourceOptions(depends_on=[log_group]),
                tags=self.tags,
            )
