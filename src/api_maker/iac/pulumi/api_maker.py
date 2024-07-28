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

        self.lambda_function = self.deploy_lambda()
        self.gateway = self.lambda_function.invoke_arn.apply(self.deploy_gateway)
        self.stage = self.deploy_stage()

        # Directly use the stage's invoke_url for endpoint_url
        self.endpoint_url = self.stage.invoke_url
        if os.environ.get("AWS_PROFILE") == "localstack":
            self.endpoint_url = self.gateway.id.apply(
                lambda gateway_id: f"http://localhost:4566/restapis/{gateway_id}/dev/_user_request_"
            )

        # Directly use the stage's invoke_url for endpoint_url
        self.register_outputs(
            {"gateway_id": self.gateway.id, "endpoint_url": self.endpoint_url}
        )

    def deploy_lambda(self) -> aws.lambda_.Function:
        api_maker_source = "/Users/clydedanielrepik/workspace/api_maker/src/api_maker"

        self.archive_builder = PythonArchiveBuilder(
            name=f"{self.name}-archive-builder",
            sources={
                "api_maker": api_maker_source,
                "api_spec.yaml": self.api_spec,
                "app.py": pkgutil.get_data("api_maker", "iac/handler.py").decode(
                    "utf-8"
                ),
            },
            requirements=[
                "pyyaml",
                "psycopg2-binary",
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

        return lambda_function.lambda_

    def deploy_gateway(self, function_invoke_arn):
        ModelFactory.load_yaml(self.props.get("api_spec"))

        return aws.apigateway.RestApi(
            f"{self.name}-rest-api",
            name=f"{self.name}-rest-api",
            body=GatewaySpec(
                function_name=self.function_name,
                function_invoke_arn=function_invoke_arn,
                enable_cors=True,
            ).as_yaml(),
            fail_on_warnings=True,
        )

    def deploy_stage(self):
        deployment = aws.apigateway.Deployment(
            f"{self.name}-deployment", rest_api=self.gateway.id
        )

        return aws.apigateway.Stage(
            f"{self.name}-stage",
            rest_api=self.gateway.id,
            deployment=deployment.id,
            stage_name="dev",
        )
