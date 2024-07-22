import os
import pkgutil
from typing import Any, Awaitable, Mapping, Union

import pulumi
import pulumi_aws as aws

from api_maker.utils.logger import logger, DEBUG, write_logging_file
from api_maker.utils.model_factory import ModelFactory
from api_maker.iac.gateway_spec import GatewaySpec
from api_maker.cloudprints.python_archive_builder import PythonArchiveBuilder
from api_maker.cloudprints.pulumi.lambda_ import PythonFunctionCloudprint

log = logger(__name__)


class APIMaker(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        props: Mapping[str, Union[Any, Awaitable[Any], pulumi.Output[Any]]],
        opts: pulumi.ResourceOptions = None,
        remote: bool = False,
    ) -> None:
        super().__init__("api_maker", name, props, opts, remote)

        self.name = name
        self.props = props
        self.api_spec = str(props.get("api_spec", None))
        assert self.api_spec, "api_spec is not set, a location must be provided."

        self.secrets = props.get("secrets")
        assert self.secrets, "Missing secrets map"

        self.function_name = f"{self.name}-api-maker"

        lambda_function = self.deploy_lambda()
        lambda_function.invoke_arn.apply(
            lambda invoke_arn: self.deploy_gateway(invoke_arn)
        )

    def deploy_lambda(self) -> PythonFunctionCloudprint:
        api_maker_source = "/Users/clydedanielrepik/workspace/api_maker/src/api_maker"

        self.archive_builder = PythonArchiveBuilder(
            name=f"{self.name}-archive-builder",
            sources={
                "api_maker": api_maker_source,
                "api_spec.yaml": self.api_spec,
                "app.py": pkgutil.get_data("api_maker", "iac/handler.py").decode(
                    "utf-8"
                ),  # noqa E501
            },
            requirements=[
                "psycopg2-binary",
                "pyyaml",
            ],
            working_dir="temp",
        )

        environment = {"SECRETS": self.secrets}
        if os.environ.get("AWS_PROFILE") == "localstack":
            environment.update(
                {
                    "AWS_ACCESS_KEY_ID": "test",
                    "AWS_SECRET_ACCESS_KEY": "test",
                    "AWS_ENDPOINT_URL": "http://localstack:4566",
                }
            )

        lambda_function = PythonFunctionCloudprint(
            name=self.function_name,
            hash=self.archive_builder.hash(),
            handler="app.lambda_handler",
            archive_location=self.archive_builder.location(),
            environment=environment,
            memory_size=self.props.get("memory_size", 128),
            reserved_concurrent_executions=self.props.get(
                "reserved_concurrent_executions", -1
            ),
            timeout=self.props.get("timeout", 30),
            tags=self.props.get("tags", {}),
            vpc_config=self.props.get("vpc_config", {}),
        )

        # Add permission for API Gateway to invoke the Lambda function
        aws.lambda_.Permission(
            f"{self.function_name}-invoke-permission",
            action="lambda:InvokeFunction",
            function=lambda_function.lambda_.name,
            principal="apigateway.amazonaws.com",
            source_arn=pulumi.Output.concat(
                "arn:aws:execute-api:",
                os.getenv("AWS_REGION", "us-east-1"),
                ":",
                aws.get_caller_identity().account_id,
                ":",
                "*",
            ),
        )

        return lambda_function

    def deploy_gateway(self, invoke_arn: str):
        ModelFactory.load_yaml(self.props.get("api_spec"))

        body = GatewaySpec(
            function_name=self.function_name,
            function_invoke_arn=invoke_arn,
            enable_cors=True,
        ).as_yaml()

        if log.isEnabledFor(DEBUG):
            write_logging_file(f"{self.name}-gateway-doc.yaml", body)

        gateway = aws.apigateway.RestApi(
            f"{self.name}-http-api",
            name=f"{self.name}-http-api",
            body=body,
            fail_on_warnings=True,
        )

        deployment = aws.apigateway.Deployment(
            f"{self.name}-deployment", rest_api=gateway.id
        )

        stage = aws.apigateway.Stage(
            f"{self.name}-stage",
            rest_api=gateway.id,
            deployment=deployment.id,
            stage_name="dev",
        )

        pulumi.export("gateway-api", gateway.id)

        endpoint = stage.invoke_url.apply(
            lambda url: f"https://{gateway.id}.execute-api.{os.getenv('AWS_REGION')}.amazonaws.com/dev"  # noqa E501
        )
        pulumi.export("endpoint-url", endpoint)
