from api_maker.dao.sql_query_handler import SQLSchemaQueryHandler
from api_maker.dao.sql_select_query_handler import SQLSelectSchemaQueryHandler
from api_maker.operation import Operation
from api_maker.utils.model_factory import SchemaObjectAssociation


class SQLSubselectSchemaQueryHandler(SQLSelectSchemaQueryHandler):
    def __init__(
        self,
        operation: Operation,
        relation: SchemaObjectAssociation,
        parent_generator: SQLSchemaQueryHandler,
    ) -> None:
        super().__init__(
            operation, relation.child_schema_object, parent_generator.engine
        )
        self.relation = relation
        self.parent_generator = parent_generator

    def selection_result_map(self) -> dict:
        filter_str = self.operation.metadata_params.get("properties", "")
        result = {self.relation.child_property.name: self.relation.child_property}

        for relation_name, reg_exs in self.get_regex_map(filter_str).items():
            if relation_name != self.relation.name:
                continue

            schema_object = self.relation.child_schema_object

            # Filter and prefix keys for the current entity and regular expressions
            filtered_keys = self.filter_and_prefix_keys(
                reg_exs, schema_object.properties
            )

            # Extend the result map with the filtered keys
            result.update(filtered_keys)

        return result

    @property
    def placeholders(self) -> dict:
        return self.search_placeholders

    @property
    def sql(self) -> str | None:
        if len(self.select_list_columns) == 1:  # then it only contains the key
            return None

        sql = (
            f"SELECT {self.select_list} "
            + f"FROM {self.relation.child_schema_object.table_name} "
            + f"WHERE {self.relation.child_property.column_name} "
            + f"IN ( SELECT {self.relation.parent_property.column_name} "
            + f"FROM {self.parent_generator.table_expression}"
            + f"{self.parent_generator.search_condition} "
            #            + f"{order_by} {limit} {offset})"
            + ")"
        )
        self.search_placeholders = self.parent_generator.search_placeholders
        #        self._execute_sql(args["cursor"], sql, query_parameters)
        return sql
