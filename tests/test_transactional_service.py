from datetime import datetime
import json
import os

import pytest

from test_connection_factory import secrets_map, install_secrets
from api_maker.utils.app_exception import ApplicationException
from api_maker.utils.model_factory import ModelFactory
from api_maker.utils.logger import logger
from api_maker.operation import Operation
from api_maker.services.transactional_service import TransactionalService

log = logger(__name__)


class TestTransactionalService:

    def test_crud_service(self):
        """
        Integration test to check insert
        """
        ModelFactory.load_spec()
        install_secrets()
        os.environ["SECRETS_MAP"] = secrets_map

        # test insert/create
        transactional_service = TransactionalService()
        operation = Operation(
            entity="media_type",
            action="create",
            store_params={
                "media_type_id": 9000,
                "name": "X-Ray"
            },
        )

        result = transactional_service.execute(operation)
        log.info(f"result: {json.dumps(result, indent=4)}")
        assert result[0]["name"] == "X-Ray"


        # test select/read
        operation = Operation(
            entity="media_type",
            action="read",
            query_params={"media_type_id": 9000},
        )
        result = transactional_service.execute(operation)

        log.info(f"result: {result}")
        log.info(f"result: {json.dumps(result, indent=4)}")
        assert result[0]["media_type_id"] == 9000
        assert result[0]["name"] == "X-Ray"

        # test update
        operation = Operation(
            entity="media_type",
            action="update",
            query_params={
                "media_type_id": 9000
            },
            store_params={"name": "Ray gun"},
        )

        result = transactional_service.execute(operation)

        log.info(f"result: {json.dumps(result, indent=4)}")
        assert len(result) == 1
        assert result[0]["name"] == "Ray gun"

        # test delete
        operation = Operation(
            entity="media_type",
            action="delete",
            query_params={
                "media_type_id": 9000
            },
        )

        result = transactional_service.execute(operation)

        log.info(f"result: {json.dumps(result, indent=4)}")
        assert len(result) == 1
        assert result[0]["media_type_id"] == 9000
        assert result[0]["name"] == "Ray gun"

        # test select/read
        operation = Operation(
            entity="media_type",
            action="read",
            query_params={"media_type_id": 9000},
        )
        result = transactional_service.execute(operation)

        log.info(f"result: {result}")
        log.info(f"result: {json.dumps(result, indent=4)}")
        assert len(result) == 0


    def test_crud_with_timestamp_service(self):
        """
        Integration test to check insert
        """
        ModelFactory.load_spec()
        install_secrets()
        os.environ["SECRETS_MAP"] = secrets_map

        # test insert/create
        transactional_service = TransactionalService()
        operation = Operation(
            entity="invoice",
            action="create",
            store_params={
                "invoice_date": datetime.now().isoformat(),
                "customer_id": 2,
                "billing_address": "address",
                "billing_city": "billing_city",
                "billing_state": "billing_state",
                "billing_country": "billing_country",
                "billing_postal_code": "code",
                "total": "3.1459",
            },
        )

        result = transactional_service.execute(operation)
        log.info(f"result: {json.dumps(result, indent=4)}")
        assert result[0]["billing_address"] == "address"

        invoice_id = result[0]["invoice_id"]

        # test select/read
        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": invoice_id},
            metadata_params={"_properties": ".* customer:.* line_items:.*"},
        )
        result = transactional_service.execute(operation)

        log.info(f"result: {result}")
        log.info(f"result: {json.dumps(result, indent=4)}")
        assert result[0]["invoice_id"] == invoice_id
        assert result[0]["customer"]["customer_id"] == 2
        assert len(result[0]["line_items"]) == 0

        invoice_id = result[0]["invoice_id"]

        # try update without concurrency value. should fail
        try:
            operation = Operation(
                entity="invoice",
                action="update",
                query_params={"invoice_id": invoice_id},
            )

            result = transactional_service.execute(operation)
            assert len(result) == 1
        except ApplicationException as e:
            assert (
                e.message
                == "Missing required concurrency management property.  schema_object: invoice, property: last_updated"
            )

        # test update
        operation = Operation(
            entity="invoice",
            action="update",
            query_params={
                "invoice_id": invoice_id,
                "last_updated": result[0]["last_updated"],
            },
            store_params={"billing_address": "updated address"},
        )

        result = transactional_service.execute(operation)

        log.info(f"result: {json.dumps(result, indent=4)}")
        assert len(result) == 1
        assert result[0]["billing_address"] == "updated address"

        # delete without concurrency value. should fail
        try:
            operation = Operation(
                entity="invoice",
                action="delete",
                query_params={"invoice_id": invoice_id},
            )

            result = transactional_service.execute(operation)
            assert False, "Exception not thrown"
        except ApplicationException as e:
            assert (
                e.message
                == "Missing required concurrency management property.  schema_object: invoice, property: last_updated"
            )

        # test delete
        operation = Operation(
            entity="invoice",
            action="delete",
            query_params={
                "invoice_id": invoice_id,
                "last_updated": result[0]["last_updated"],
            },
        )

        result = transactional_service.execute(operation)

        log.info(f"result: {json.dumps(result, indent=4)}")
        assert len(result) == 1
        assert result[0]["invoice_id"] == invoice_id
        assert result[0]["customer_id"] == 2

        # test select/read
        operation = Operation(
            entity="invoice",
            action="read",
            query_params={"invoice_id": invoice_id},
        )
        result = transactional_service.execute(operation)

        log.info(f"result: {result}")
        log.info(f"result: {json.dumps(result, indent=4)}")
        assert len(result) == 0


    def test_crud_with_uuid_service(self):
        """
        Integration test to check insert
        """
        ModelFactory.load_spec()
        install_secrets()
        os.environ["SECRETS_MAP"] = secrets_map

        # test insert/create
        transactional_service = TransactionalService()
        operation = Operation(
            entity="customer",
            action="create",
            store_params={
                "first_name": "John",
                "last_name": "Doe",
                "company": "Acme Inc.",
                "address": "123 Main St",
                "city": "Anytown",
                "state": "California",
                "country": "United States",
                "postal_code": "12345",
                "phone": "123-456-7890",
                "fax": "123-456-7890",
                "email": "john.doe@example.com",
                "support_rep_id": 3,
            },
        )

        result = transactional_service.execute(operation)
        log.info(f"result: {json.dumps(result, indent=4)}")
        assert result[0]["address"] == "123 Main St"

        customer_id = result[0]["customer_id"]

        # test select/read
        operation = Operation(
            entity="customer",
            action="read",
            query_params={"customer_id": customer_id}
        )
        result = transactional_service.execute(operation)

        log.info(f"result: {result}")
        log.info(f"result: {json.dumps(result, indent=4)}")
        assert result[0]["customer_id"] == customer_id
        assert result[0]["support_rep_id"] == 3

        # try update without concurrency value. should fail
        try:
            operation = Operation(
                entity="customer",
                action="update",
                query_params={"customer_id": customer_id},
                store_params={"address": "321 Broad St"},
            )

            result = transactional_service.execute(operation)
            assert len(result) == 1
        except ApplicationException as e:
            assert (
                e.message
                == "Missing required concurrency management property.  schema_object: customer, property: version_stamp"
            )

        # test update
        operation = Operation(
            entity="customer",
            action="update",
            query_params={
                "customer_id": customer_id,
                "version_stamp": result[0]["version_stamp"],
            },
            store_params={"address": "321 Broad St"},
        )

        result = transactional_service.execute(operation)

        log.info(f"result: {json.dumps(result, indent=4)}")
        assert len(result) == 1
        assert result[0]["address"] == "321 Broad St"

        try:
          # test delete without version stamp
          operation = Operation(
              entity="customer",
              action="delete",
              query_params={
                  "customer_id": customer_id
              },
          )

          result = transactional_service.execute(operation)
        except ApplicationException as e:
            assert e.message == "Missing required concurrency management property.  schema_object: customer, property: version_stamp"
            
        # test delete
        operation = Operation(
            entity="customer",
            action="delete",
            query_params={
                "customer_id": customer_id,
                "version_stamp": result[0]["version_stamp"],
            },
        )

        result = transactional_service.execute(operation)

        log.info(f"result: {json.dumps(result, indent=4)}")
        assert len(result) == 1
        assert result[0]["customer_id"] == customer_id

        # test select/read
        operation = Operation(
            entity="customer",
            action="read",
            query_params={"customer_id": customer_id}
        )
        result = transactional_service.execute(operation)

        log.info(f"result: {result}")
        log.info(f"result: {json.dumps(result, indent=4)}")
        assert len(result) == 0
