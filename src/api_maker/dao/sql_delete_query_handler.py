from api_maker.dao.sql_query_handler import SQLSchemaQueryHandler
from api_maker.operation import Operation
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.model_factory import SchemaObject


class SQLDeleteSchemaQueryHandler(SQLSchemaQueryHandler):
    def __init__(
        self, operation: Operation, schema_object: SchemaObject, engine: str
    ) -> None:
        super().__init__(operation, schema_object, engine)

    @property
    def sql(self) -> str:
        concurrency_property = self.schema_object.concurrency_property
        if concurrency_property:
            if not self.operation.query_params.get(concurrency_property.name):
                raise ApplicationException(
                    400,
                    "Missing required concurrency management property.  "
                    + f"schema_object: {self.schema_object.operation_id}, "
                    + f"property: {concurrency_property.name}",
                )
            if self.operation.store_params.get(concurrency_property.name):
                raise ApplicationException(
                    400,
                    "For updating concurrency managed schema objects the current "
                    + "version may not be supplied as a storage parameter.  "
                    + f"schema_object: {self.schema_object.operation_id}, "
                    + f"property: {concurrency_property.name}",
                )

        return (
            f"DELETE FROM {self.table_expression}{self.search_condition} "
            + f"RETURNING {self.select_list}"
        )
