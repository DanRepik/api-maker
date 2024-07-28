import json
import pulumi

from api_maker.iac.pulumi.api_maker import APIMaker

api_maker = APIMaker(
    "chinook_postgres",
    props={
        "api_spec": "./chinook_api.yaml",
        "secrets": json.dumps({"chinook": "chinook/postgres"}),
        #        "vpc_config": {
        #            "vpc_id": "vpc-09c3be3143de22c11",
        #            "security_group_ids": ["sg-00ae9f041183f0fc3"],
        #            "subnet_ids": ["subnet-0ee4d6ffcd06d2148", "subnet-028152ebbd6d58aee"],
        #        },
        "tags": {"project": pulumi.get_project(), "stack": pulumi.get_stack()},
    },
)

pulumi.export("gateway_api", api_maker.gateway.id)
pulumi.export("endpoint_url", api_maker.endpoint_url)
