import copy
import json
import re
import yaml
from typing import Union

from api_maker.utils.model_factory import (
    ModelFactory,
    SchemaObject,
    SchemaObjectProperty,
)
from api_maker.utils.logger import logger

log = logger(__name__)


def remove_non_alphanumeric(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", text)


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


class GatewaySpec:
    api_spec: dict
    function_name: str
    function_invoke_arn: str

    def __init__(
        self, *, function_name: str, function_invoke_arn, enable_cors: bool = False
    ):
        self.function_name = function_name
        self.function_invoke_arn = function_invoke_arn
        log.info(f"invoke_arn: {function_invoke_arn}")
        document = ModelFactory.spec

        self.api_spec = dict(self.remove_custom_attributes(copy.deepcopy(document)))
        if enable_cors:
            self.enable_cors()

        for schema_name in ModelFactory.get_schema_names():
            self.generate_crud_operations(
                schema_name, ModelFactory.get_schema_object(schema_name)
            )

        self.fix_schema_names()

    def as_json(self):
        return json.dumps(self.api_spec)

    def as_yaml(self):
        return yaml.dump(self.api_spec, Dumper=NoAliasDumper, default_flow_style=False)

    def remove_custom_attributes(self, obj):
        return self.remove_attributes(obj, "^x-am-.*$")

    def remove_attributes(self, obj, pattern) -> Union[dict, list]:
        """
        Remove attributes from an object that match a regular expression pattern.

        Args:
            obj: The object from which attributes will be removed.
            pattern: The regular expression pattern to match attributes.

        Returns:
            obj
        """
        if isinstance(obj, dict):
            return {
                key: self.remove_attributes(value, pattern)
                for key, value in obj.items()
                if not re.match(pattern, key)
            }
        elif isinstance(obj, list):
            return [self.remove_attributes(item, pattern) for item in obj]
        else:
            return obj

    def fix_schema_names(self):
        if "components" in self.api_spec and "schemas" in self.api_spec["components"]:
            schemas = self.api_spec["components"]["schemas"]
            fixed_schemas = {}
            name_mapping = {}
            for schema_name, schema_obj in schemas.items():
                fixed_name = remove_non_alphanumeric(schema_name)
                fixed_schemas[fixed_name] = schema_obj
                name_mapping[schema_name] = fixed_name

            self.api_spec["components"]["schemas"] = fixed_schemas
            self.fix_references(self.api_spec, name_mapping)

    def fix_references(self, obj, name_mapping):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value.startswith("#/components/schemas/"):
                    original_name = value.split("/")[-1]
                    if original_name in name_mapping:
                        obj[key] = f"#/components/schemas/{name_mapping[original_name]}"
                else:
                    self.fix_references(value, name_mapping)
        elif isinstance(obj, list):
            for item in obj:
                self.fix_references(item, name_mapping)

    def remove_object_or_array_types(self, d):
        """
        Remove items from the dictionary where the value of 'type' is 'object' or 'array'.

        Args:
            d (dict): The input dictionary to process.

        Returns:
            dict: The processed dictionary with the specified items removed.
        """
        # Create a new dictionary to avoid modifying the input dictionary directly
        filtered_dict = {}
        for key, value in d.items():
            # Check if the value is a dictionary and has a 'type'
            # key with value 'object' or 'array'
            if isinstance(value, dict) and value.get("type") in ["object", "array"]:
                continue
            else:
                filtered_dict[key] = value

        return self.remove_custom_attributes(filtered_dict)

    def add_custom_authentication(self, authentication_invoke_arn: str):
        components = self.api_spec.get("components", None)
        if components:
            components["securitySchemes"] = {
                "auth0": {
                    "type": "apiKey",
                    "name": "Authorization",
                    "in": "header",
                    "x-amazon-apigateway-authtype": "custom",
                    "x-amazon-apigateway-authorizer": {
                        "type": "token",
                        "authorizerUri": authentication_invoke_arn,
                        "identityValidationExpression": "^Bearer [-0-9a-zA-Z._]*$",
                        "identitySource": "method.request.header.Authorization",
                        "authorizerResultTtlInSeconds": 60,
                    },
                }
            }

    def add_operation(self, path: str, method: str, operation: dict):
        operation["x-function-name"] = self.function_name
        operation["x-amazon-apigateway-integration"] = {
            "type": "aws_proxy",
            "uri": self.function_invoke_arn,
            "httpMethod": "POST",
            "responses": {"default": {"statusCode": "200"}},
            "passthroughBehavior": "when_no_match",
            "payloadFormatVersion": "1.0",
        }

        self.api_spec.setdefault("paths", {}).setdefault(path, {})[method] = operation

    def enable_cors(self):
        self.add_operation(
            "/{proxy+}",
            "options",
            {
                "responses": {
                    "200": {
                        "description": "200 response",
                        "headers": {
                            "Access-Control-Allow-Origin": {
                                "schema": {"type": "string"}
                            },
                            "Access-Control-Allow-Methods": {
                                "schema": {"type": "string"}
                            },
                            "Access-Control-Allow-Headers": {
                                "schema": {"type": "string"}
                            },
                        },
                        "content": {},
                    },
                },
                "x-amazon-apigateway-integration": {
                    "responses": {
                        "default": {
                            "statusCode": "200",
                            "responseParameters": {
                                "method.response.header.Access-Control-Allow-Methods": "'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT'",  # noqa E501
                                "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",  # noqa E501
                                "method.response.header.Access-Control-Allow-Origin": "'*'",  # noqa E501
                            },
                            "responseTemplates": {
                                "application/json": "",
                            },
                        },
                    },
                    "passthroughBehavior": "never",
                    "type": "mock",
                },
            },
        )

        self.api_spec["x-amazon-apigateway-cors"] = {
            "allowOrigins": ["*"],
            "allowCredentials": True,
            "allowMethods": [
                "GET",
                "POST",
                "OPTIONS",
                "PUT",
                "PATCH",
                "DELETE",
            ],
            "allowHeaders": [
                "Origin",
                "X-Requested-With",
                "Content-Type",
                "Accept",
                "Authorization",
            ],
        }

    def generate_regex(self, property: SchemaObjectProperty):
        regex_pattern = ""

        if property.api_type == "string":
            if property.max_length is not None:
                regex_pattern += f"{{0,{property.max_length}}}"

            if property.min_length is not None:
                regex_pattern += f"{{{property.min_length},}}"

            if property.pattern is not None:
                regex_pattern += f"({property.pattern})"

        if property.api_type == "date":
            # Assuming ISO 8601 date format (YYYY-MM-DD)
            regex_pattern = r"\d{4}-\d{2}-\d{2}"

        elif property.api_type == "date-time":
            regex_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"

        elif property.api_type == "integer":
            regex_pattern = r"\d+"

        elif property.api_type == "number":
            regex_pattern = r"\d+(\.\d+)"

        if len(regex_pattern) == 0:
            regex_pattern = ".*"

        return (
            f"^(({regex_pattern})|lt::|le::|eq::|ne::|ge::|gt::"
            + f"|between::({regex_pattern}),"
            + f"|not-between::({regex_pattern}),"
            + f"|in::(({regex_pattern}),)*)$"
            + f"|not-in::(({regex_pattern}),)*)$"
        )

    def generate_query_parameters(self, schema_object: SchemaObject):
        parameters = []
        for property_name, property_details in schema_object.properties.items():
            parameter = {
                "in": "query",
                "name": property_name,
                "required": False,
                "schema": {
                    "type": property_details.type,
                },
                "description": f"Filter by {property_name}",
            }
            parameters.append(parameter)
        return parameters

    def __list_of_schema(self, schema_name: str):
        fixed_schema_name = remove_non_alphanumeric(schema_name)
        return {
            "application/json": {
                "schema": {
                    "type": "array",
                    "items": {"$ref": f"#/components/schemas/{fixed_schema_name}"},
                }
            }
        }

    def generate_crud_operations(self, schema_name, schema_object: SchemaObject):
        path = f"/{schema_name.lower()}"
        log.info(f"xx path: {path}")
        self.generate_create_operation(path, schema_name, schema_object)
        self.generate_get_by_id_operation(path, schema_name, schema_object)
        self.generate_get_many_operation(path, schema_name, schema_object)
        self.generate_update_by_id_operation(path, schema_name, schema_object)
        self.generate_update_with_cc_operation(path, schema_name, schema_object)
        self.generate_update_many_operation(path, schema_name, schema_object)
        self.generate_delete_by_id_operation(path, schema_name, schema_object)
        self.generate_delete_with_cc_operation(path, schema_name, schema_object)
        self.generate_delete_many_operation(path, schema_name, schema_object)

    def generate_create_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        self.add_operation(
            path,
            "post",
            {
                "summary": f"Create a new {schema_name}",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": self.remove_object_or_array_types(
                                    schema_object.schema_object["properties"]
                                ),
                                "required": schema_object.required,
                            }
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": f"{schema_name} created successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
        )

    def generate_get_many_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        self.add_operation(
            path,
            "get",
            {
                "summary": f"Retrieve all {schema_name}",
                "parameters": self.generate_query_parameters(schema_object),
                "responses": {
                    "200": {
                        "description": f"A list of {schema_name}.",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
        )

    def generate_get_by_id_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        key = schema_object.primary_key
        if not key:
            return

        self.add_operation(
            f"{path}/{{{key.name}}}",
            "get",
            {
                "summary": f"Retrieve {schema_name} by {key.name}",
                "parameters": [
                    {
                        "name": key.name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to get",
                        "required": True,
                        "schema": {"type": key.api_type},
                    }
                ],
                "responses": {
                    200: {
                        "description": f"A list of {schema_name}.",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
        )

    def generate_update_by_id_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        if schema_object.concurrency_property:
            return

        key = schema_object.primary_key
        if not key:
            return

        # Update operation
        self.add_operation(
            f"{path}/{{{key.name}}}",
            "put",
            {
                "summary": f"Update an existing {schema_name} by {key.name}",
                "parameters": [
                    {
                        "name": key.name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": key.api_type},
                    }
                ],
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": self.remove_object_or_array_types(
                                    schema_object.schema_object["properties"]
                                ),
                                "required": [],  # No properties are marked as required
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{schema_name} updated successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
        )

    def generate_update_with_cc_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        # Update operation
        key = schema_object.primary_key
        if not key:
            return

        cc_property = schema_object.concurrency_property
        if not cc_property:
            return

        self.add_operation(
            f"{path}/{{{key.name}}}/{cc_property.name}/{{{cc_property.name}}}",
            "put",
            {
                "summary": f"Update an existing {schema_name} by ID",
                "parameters": [
                    {
                        "name": key.name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": key.api_type},
                    },
                    {
                        "name": cc_property.name,
                        "in": "path",
                        "description": (
                            cc_property.name + " of the " + schema_name + " to update"
                        ),
                        "required": True,
                        "schema": {"type": cc_property.api_type},
                    },
                ],
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": self.remove_object_or_array_types(
                                    schema_object.schema_object["properties"]
                                ),
                                "required": [],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{schema_name} updated successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
        )

    def generate_update_many_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        if schema_object.concurrency_property:
            return

        # Update operation
        self.add_operation(
            path,
            "put",
            {
                "summary": f"Update an existing {schema_name} by ID",
                "parameters": self.generate_query_parameters(schema_object),
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": self.remove_object_or_array_types(
                                    schema_object.schema_object["properties"]
                                ),
                                "required": [],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{schema_name} updated successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
        )

    def generate_delete_with_cc_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        cc_property = schema_object.concurrency_property
        if not cc_property:
            return

        key = schema_object.primary_key
        if not key:
            return

        self.add_operation(
            f"{path}/{{{key.name}}}/{cc_property.name}/{{{cc_property.name}}}",
            "delete",
            {
                "summary": f"Delete an existing {schema_name} by ID",
                "parameters": [
                    {
                        "name": key.name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": key.api_type},
                    },
                    {
                        "name": cc_property.name,
                        "in": "path",
                        "description": (
                            f"{cc_property.name} of the {schema_name} to update"
                        ),
                        "required": True,
                        "schema": {"type": cc_property.api_type},
                    },
                ],
                "responses": {
                    "204": {
                        "description": f"{schema_name} deleted successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
        )

    def generate_delete_by_id_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        if schema_object.concurrency_property:
            return

        key = schema_object.primary_key
        if not key:
            return

        self.add_operation(
            f"{path}/{{{key.name}}}",
            "delete",
            {
                "summary": f"Delete an existing {schema_name} by {key.name}",
                "parameters": [
                    {
                        "name": key.name,
                        "in": "path",
                        "description": f"ID of the {schema_name} to update",
                        "required": True,
                        "schema": {"type": key.api_type},
                    }
                ],
                "responses": {
                    "204": {
                        "description": f"{schema_name} deleted successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
        )

    def generate_delete_many_operation(
        self, path: str, schema_name: str, schema_object: SchemaObject
    ):
        if schema_object.concurrency_property:
            return

        self.add_operation(
            path,
            "delete",
            {
                "summary": f"Delete many existing {schema_name} using query",
                "parameters": self.generate_query_parameters(schema_object),
                "responses": {
                    "204": {
                        "description": f"{schema_name} deleted successfully",
                        "content": self.__list_of_schema(schema_name),
                    }
                },
            },
        )
