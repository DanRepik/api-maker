import json
import os

import pulumi

from api_maker.iac.pulumi.api_maker import APIMaker
from postgres_initializer import PostgresInitializer, PostgresInitializerArgs

secrets = json.dumps({"chinook": "chinook/postgres"})
tags = {"project": pulumi.get_project(), "stack": pulumi.get_stack()}

stack_output = {
    "private_subnet_1": "subnet-060ce29fc7236b25a",
    "private_subnet_2": "subnet-079f1e8b9c680a776",
    "public_subnet_1": "subnet-0f103030ec890ad64",
    "public_subnet_2": "subnet-03b7d62adc7b5339f",
    "rds_instance_endpoint": "rds-postgres-postgres-rds-instance035f81e.cyxalzioml7u.us-east-1.rds.amazonaws.com:5432",
    "secret_version_arn": "[secret]",
    "security_group": "sg-02362d9040284e379",
    "vpc_id": "vpc-0da98adb18bc244da",
}


# sg-028e7c9f86f37ac3b

vpc_config = {
    "vpc_id": stack_output["vpc_id"],
    "security_group_ids": [stack_output["security_group"]],
    "subnet_ids": [stack_output["private_subnet_1"], stack_output["private_subnet_2"]],
}

api_maker = APIMaker(
    "chinook",
    props={
        "api_spec": "./chinook_api.yaml",
        "secrets": secrets,
        "vpc_config": vpc_config,
        "tags": tags,
    },
)

if os.environ.get("INITAILIZER"):
    PostgresInitializer(
        "chinook-init",
        PostgresInitializerArgs(
            secrets=secrets,
            database="chinook",
            #            vpc_config=vpc_config,
            tags=tags,
        ),
    )


pulumi.export("gateway_api", api_maker.gateway.id)
pulumi.export("endpoint_url", api_maker.endpoint_url)
