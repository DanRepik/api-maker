import json
import os

import pulumi

from api_maker.iac.pulumi.api_maker import APIMaker
from postgres_initializer import PostgresInitializer, PostgresInitializerArgs

secrets = json.dumps({"chinook": "chinook/postgres"})
tags = {"project": pulumi.get_project(), "stack": pulumi.get_stack()}

vpc_config = {
    "vpc_id": "vpc-03d0b5f08f120f57c",
    "security_group_ids": ["sg-07efca72d1041f9f3"],
    "subnet_ids": [
        "subnet-0deb799cdd3bc90d7",
        "subnet-02b4eaee27ddd71c4",
    ],
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
            secrets=secrets, database="chinook", vpc_config=vpc_config, tags=tags
        ),
    )


pulumi.export("gateway_api", api_maker.gateway.id)
pulumi.export("endpoint_url", api_maker.endpoint_url)
