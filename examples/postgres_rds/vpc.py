import pulumi
import pulumi_aws as aws


class VpcComponent(pulumi.ComponentResource):
    def __init__(self, name: str, cidr_block: str, opts: pulumi.ResourceOptions = None):
        super().__init__("custom:resource:VpcComponent", name, {}, opts)

        self.vpc = aws.ec2.Vpc(
            f"{name}-vpc",
            cidr_block=cidr_block,
            enable_dns_support=True,
            enable_dns_hostnames=True,
            tags={"Name": f"{name}-vpc"},
        )

        self.igw = aws.ec2.InternetGateway(
            f"{name}-igw", vpc_id=self.vpc.id, tags={"Name": f"{name}-igw"}
        )

        self.public_subnet1 = aws.ec2.Subnet(
            f"{name}-public-subnet-1",
            vpc_id=self.vpc.id,
            cidr_block="10.0.1.0/24",
            map_public_ip_on_launch=True,
            availability_zone="us-east-1a",
            tags={"Name": f"{name}-public-subnet-1"},
        )

        self.public_subnet2 = aws.ec2.Subnet(
            f"{name}-public-subnet-2",
            vpc_id=self.vpc.id,
            cidr_block="10.0.2.0/24",
            map_public_ip_on_launch=True,
            availability_zone="us-east-1b",
            tags={"Name": f"{name}-public-subnet-2"},
        )

        self.public_route_table = aws.ec2.RouteTable(
            f"{name}-public-route-table",
            vpc_id=self.vpc.id,
            routes=[
                {
                    "cidr_block": "0.0.0.0/0",
                    "gateway_id": self.igw.id,
                }
            ],
            tags={"Name": f"{name}-public-route-table"},
        )

        self.public_route_table_assoc1 = aws.ec2.RouteTableAssociation(
            f"{name}-public-route-table-assoc-1",
            subnet_id=self.public_subnet1.id,
            route_table_id=self.public_route_table.id,
        )

        self.public_route_table_assoc2 = aws.ec2.RouteTableAssociation(
            f"{name}-public-route-table-assoc-2",
            subnet_id=self.public_subnet2.id,
            route_table_id=self.public_route_table.id,
        )

        self.private_subnet1 = aws.ec2.Subnet(
            f"{name}-private-subnet-1",
            vpc_id=self.vpc.id,
            cidr_block="10.0.3.0/24",
            availability_zone="us-east-1a",
            tags={"Name": f"{name}-private-subnet-1"},
        )

        self.private_subnet2 = aws.ec2.Subnet(
            f"{name}-private-subnet-2",
            vpc_id=self.vpc.id,
            cidr_block="10.0.4.0/24",
            availability_zone="us-east-1b",
            tags={"Name": f"{name}-private-subnet-2"},
        )

        self.eip = aws.ec2.Eip(
            f"{name}-eip",
            vpc=True,
            tags={"Name": f"{name}-eip"},
        )

        self.nat_gateway = aws.ec2.NatGateway(
            f"{name}-nat-gateway",
            subnet_id=self.public_subnet1.id,
            allocation_id=self.eip.id,
            tags={"Name": f"{name}-nat-gateway"},
        )

        self.private_route_table = aws.ec2.RouteTable(
            f"{name}-private-route-table",
            vpc_id=self.vpc.id,
            routes=[
                {
                    "cidr_block": "0.0.0.0/0",
                    "nat_gateway_id": self.nat_gateway.id,
                }
            ],
            tags={"Name": f"{name}-private-route-table"},
        )

        self.private_route_table_assoc1 = aws.ec2.RouteTableAssociation(
            f"{name}-private-route-table-assoc-1",
            subnet_id=self.private_subnet1.id,
            route_table_id=self.private_route_table.id,
        )

        self.private_route_table_assoc2 = aws.ec2.RouteTableAssociation(
            f"{name}-private-route-table-assoc-2",
            subnet_id=self.private_subnet2.id,
            route_table_id=self.private_route_table.id,
        )

        # Create a Security Group for the VPC
        self.security_group = aws.ec2.SecurityGroup(
            f"{name}-security-group",
            vpc_id=self.vpc.id,
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
            tags={"Name": f"{name}-security-group"},
        )

        # Create a VPC Endpoint for Secrets Manager
        self.vpc_endpoint = aws.ec2.VpcEndpoint(
            f"{name}-secretsmanager-endpoint",
            vpc_id=self.vpc.id,
            service_name="com.amazonaws.us-east-1.secretsmanager",
            vpc_endpoint_type="Interface",
            subnet_ids=[self.public_subnet1.id, self.public_subnet2.id],
            security_group_ids=[self.security_group.id],
        )

        self.register_outputs(
            {
                "vpc_id": self.vpc.id,
                "public_subnet1_id": self.public_subnet1.id,
                "public_subnet2_id": self.public_subnet2.id,
                "private_subnet1_id": self.private_subnet1.id,
                "private_subnet2_id": self.private_subnet2.id,
            }
        )
