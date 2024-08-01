from datetime import date, datetime
from typing import List
from io import UnsupportedOperation


from api_maker.connectors.connection import Connection
from api_maker.dao.sql_generator import SQLGenerator
from api_maker.utils.model_factory import SchemaObject
from api_maker.operation import Operation
from api_maker.utils.logger import logger

log = logger(__name__)


class CustomSQLGenerator(SQLGenerator):
    """Runs the supplied SQL query and returns the results"""

    def __init__(self, operation: Operation, path_option, engine: str) -> None:
        pass

    @property
    def sql(self) -> str:
        raise NotImplementedError("Subclasses should implement this method")

    @property
    def placeholders(self) -> dict:
        raise NotImplementedError("Subclasses should implement this method")

    @property
    def select_list_columns(self) -> List[str]:
        raise NotImplementedError("Subclasses should implement this method")
