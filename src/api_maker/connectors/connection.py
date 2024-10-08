import boto3
import json
import os
import re

from api_maker.utils.logger import logger
from api_maker.utils.app_exception import ApplicationException

# Initialize the logger
log = logger(__name__)

db_config_map = dict()


class Cursor:
    def execute(self, sql: str, params: dict, selection_results: dict) -> list[dict]:
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class Connection:
    def __init__(self, db_config: dict) -> None:
        super().__init__()
        self.db_config = db_config

    def engine(self) -> str:
        return self.db_config["engine"]

    def cursor(self) -> Cursor:
        raise NotImplementedError

    def commit(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
