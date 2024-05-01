# API-MAKER

Welcome to API-Maker, an open-source tool designed for rapidly building and deploying RESTful services utilizing an AWS Gateway API in conjunction with a Lambda function. Our project's primary objective is to offer a solution that demands minimal coding effort to query and manipulate data stored in relational databases.

With API-Maker, developing RESTful API's is first focused on defining components and services in the form of an Open API specification.  Objects in this specification then can be enhanced by either;

* Schema component objects can be enhanced with database table configuration, allowing API-Maker to provide RESTful CRUD services on table records. 
* Path operations can be enhanced with database connection and SQL configuration to provide service based on custom SQL.

For data read operations using HTTP GET, API-Maker provides robust data selection capability reducing the need for building custom services. To achieve this API-Maker provides the following features;

* Comparison oprands can be applied to a property when selecting data.  These operand such as; less than, between, and in, can be applied to any property for record selection.
* Associations between component objects can be defined allowing retrieval of complex objects containing associated data in a single request.
* Requesting applications can restrict the properties being returned.
* Requesting applications can select the case convention (snake or lower camel) of the ressponse results.

API-Maker is not a traditional object relational model (ORM) library but rather operates by generating and executing SQL queries to perform its services.  Generating operations this way keeps marshaling and unmarshaling objects to a minimum, ensuring efficient data retrieval and manipulation.

Deploying APIs with API-Maker involves the following steps:

1. Store the annotated API specification on Amazon S3.
2. Configure and deploy the Lambda archive.
3. Retrieve an enhanced API specification from the Lambda function.
4. Deploy the AWS Gateway API using the enhanced specification.


# Usage

When utilizing API-Maker to construct APIs, the primary focus of development lies in defining component schema objects and path operations.

Annotations on component schema objects enable seamless operations on database tables. At a minimum, these annotations configure the database and table name. However, additional annotations are available to enhance functionality:

- Renaming exposed API properties to table column names.
- Implementing concurrency control on record updates using either timestamps. UUIDs or serial numbers.
- Supporting auto-generated primary keys.
- Establishing associations with other component schema objects to enable parent-child retrievals.

Annotations to the OpenAPI specification document provides the means of mapping from API elements to database resources.  

This is done via two primary methods.

* Component Schema Objects to Database Tables - These objects can be mapped to database tables.  When this mapping is available api-maker will build supporting CRUD services.

* Path Operations to Custom SQL - This method allows attaching custom SQL to a specific operation. 


## Using API Services

When processing requests, API-Maker categorizes parameters into three categories: query, store, and metadata.

| Type     | Description                          | Methods          | Location                                |
|----------|--------------------------------------|------------------|-----------------------------------------|
| Query    | Used for selecting data.              | GET, PUT, DELETE | Request query string or path parameters |
| Store    | Values to be stored in the database. | PUT, POST        | Request body                            |
| Metadata | Instructions for processing the request | ALL              | Request query string                    |

### Selecting Data

API-Maker provides the following CRUD services for schema objects with the following URIs:

| Operation | URI    | Method  |Description |
|-----------|--------|-|-------------------------------|
| read | <object_endpoint> | GET | Query for a set of data |
| read | <object_endpoint>/{id} | GET| Selects a single record by ID.              |
| create | <object_endpoint> | POST | Insert record(s).|
| update | <object_endpoint> | PUT | Update a set of records    |
| update | <object_endpoint>/{id} | PUT | Update a record by id    |
| update | <object_endpoint>/{id}/{stamp} | PUT | Update a record with concurrency management by id    |
|delete | <object_endpoint> | DELETE | Delete a set of records |

Here, \<object_endpoint> represents the API endpoint followed by the schema object name. For example, 'https://bobsrecords.com/albums'.

The service to select a record by its ID is self-explanatory.

> Note: {id} always represents the primary key property of the schema object.

#### Selecting Sets of Data

For more flexibility in selecting sets of data, query parameters can be passed via the request query string. Additionally, requests can include relational operands to refine selection criteria.

Any property in the schema object can be used as a parameter name in the request query string. The value component can be either a simple value or a relational value.

**Simple Parameters**

For simple parameters, the implied relation is equality. Using the Chinook database, customers in Florida can be selected using the following URL:

```
https://bobsrecords.com/customer?state=FL
```

Multiple request parameters can be submitted. For example, to further restrict the set to customers in Florida with a specific support representative:

```
https://bobsrecords/customer?state=FL&support_rep_id=4
```

When the component schema object has a one-to-one association with another component schema object, requests can also search on properties of the associated object. 

For example, in the Chinook invoice schema object, where the customer property is a one-to-one associated object, invoices for customers in Florida can be selected with the following URL:

```
https://bobsrecords/invoice?customer.state=FL
```

> This feature is not applicable to one-to-many associations.

**Relational Parameters**

Relational parameters provide the means of applying relational operands to query string parameters.

For these parameters, the query string value has the relational operand followed by '::' prepended to it. The supported operands include: 'lt', 'le', 'eq', 'ne', 'ge', 'gt', 'in', 'between', 'not-in', 'not-between'.

For example, to select all employees hired after a certain date:

```
https://bobsrecords/employee?hire_date=gt::2024-01-01
```

When using range operands that require multiple values ('in', 'between', 'not-in', and 'not-between'), those values are passed as a comma-delimited list.

For example, to request employees hired in 2023;

```
https://bobsrecords.com/employee?hire_date=between::2024-01-01,2024-12-31
```

### Inserting Data

### Updating Data

Updating data is done via PUT method requests.  If in the schema component object a property has been ehanced with a version type attribute
then API-Maker restricts updates to single records.  Without a version property then normal record selection occurs allowing bulk updates 
of records.


## Query Parameters

| Methon | Operation | Query Parameters | Store Parameters | Metadata Parameters |
|--------|-----------|------------------|------------------|---------------------|
| GET    | read      |
| POST   | create    | Not accepted     | Required         |
| PUT    | update    |
| DELETE | delete    |

Request parameters for services provided by API-Maker  

### Selecting Data - GET

The `_properties` metadata parameter enables the service requester to specify the desired properties in the response. This parameter is optional, and if not provided, the service result will include objects with all properties including relational properties selected by default.

When utilized, the `_properties` parameter should be a string comprising a delimited list of regular expressions. If a property matches any of these expressions, it will be incorporated into the response. Moreover, if the schema component object contains relational properties, the composition of those properties can also be selected. In such cases, the relation name is prepended with a ':' delimiter followed by a regular expression for selecting properties of the related object.

Consider the following examples with the Chinnook invoice schema object;

| _properties | Description| 
|-------------|------------|
| .*          | Returns all invoice properties |
| .* line_items | Returns all invoice properties and the line_items associated with the invoice |
| invoice_id total | Returns just the invoice id and total |


### Metadata Parameters

| Name | Description |
| _properties | Optional, allows selecting a subset of properties returned by the request.   
A space delimited list of regular expressions |


## Open API Specification Extensions

### Schema Component Objects

By integrating API-Maker attributes into schema component objects within the OpenAPI specification document, API-Maker becomes capable of delivering CRUD (Create, Read, Update, Delete) services for efficiently managing records in a database table.

To accomplish this, attention must be given to several configuration aspects:

- **Database Configuration**: This involves addressing three primary configuration components:
  - The engine: This determines the SQL dialect to be employed.
  - The database: Indicates the database where the table resides.
  - Table name: Specifies the name of the table.

- **Primary Key**: Within the schema component, a property can be designated as the primary key. API-Maker offers support for three primary key generation strategies:
  - Manual: The responsibility for providing the key rests with the requesting application.
  - Auto: The database table autonomously generates the key.
  - Sequences: Employed in databases like Oracle, where sequence objects serve as the source of keys.

- **Concurrency Control**: Optionally, a property within the schema component can be identified as a concurrency control column, utilized to prevent service requests from overriding updates made by other requests. When a schema object includes a concurrency control property, that property must be provided as a query parameter. If the value provided does not match the one in the database, the update request fails. It's important to note that requesting services cannot set concurrency control properties using store parameters, as those values are managed by API-Maker. API-Maker supports three different concurrency control column types:
  - Timestamp: API-Maker inserts the current time in the control field, and applications must provide that timestamp.
  - UUID: Utilizes a UUID as the control value.
  - Serial: In this scenario, an integer is incremented when the record is updated.

#### Schema Component Object Attributes

These attributes map the componnent object to a database table.  

| Attribute | Description | Usage |
|-------|--------|---------|
| x-am-database | The name of the database where the table is located.   | Required, value is used to access database configuration from the runtime secrets map. |
| x-am-engine | The type of database being accessed. Determines SQL dilect to use.  | Required, must be one of 'postgres', 'oracle' or 'mysql' |
| x-am-table | The table name to perform the operations on. | Optional, defaults to schema component object name if not provided.  Must be a valid table name |

#### Schema Component Object Property Attributes

| Attribute             | Description                                                                                            | Usage                                                                                   |
|-----------------------|--------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| x-am-column-name      | Specifies the database column name if it differs from the property name.                                | Optional                                                                                |
| x-am-primary-key      | Indicates that this property serves as the primary key for the object and defines how the key is obtained. | Required; must be one of the following: manual, auto, or sequence.                       |
| x-am-concurrency-control | Marks the property for concurrency control when updating records.                                         | Optional; can be one of the following: timestamp, uuid, or serial.                        |
| x-am-sequence-name    | Specifies the database sequence to be used for generating primary keys.                                     | Required only when the primary key type is "sequence".                                    |
#### Schema Component Object Associations

API-Maker simplifies the retrieval of complex objects, including those containing nested objects or lists of objects, through the utilization of associations. These associations can be classified as either one-to-one or one-to-many and are specified within the properties of the schema component object.

By default, API_maker services return a flat object. To retrieve objects associated with the association, the request must select those properties using the '_properties' metadata parameter.

> A note on terminology regarding associations: When referring to objects in the association, `primary` represents the main object being returned. `Secondary` objects are objects attached either directly or as elements of a list attached to the primary object.

To specify these associations, properties are added to the `primary` schema component object.  These properties constain attributes that specify the association using the following attributes:

| Attribute             | Description                                          | Usage             |
|-----------------------|------------------------------------------------------|-------------------|
| x-am-schema-object    | The name of the secondary schema component object to select. | Required      |
| x-am-cardinality      | The type of association, must be either '1:1' or '1:m',                      | Optional, '1:1' by default |
| x-am-parent-property  | The name of the 'primary' property that identifies the selection key.  | Optional, defaults to `parent` primary key.  Normally needed for 1:1 associations. |
| x-am-child-property   | The name of the property in the `secondary` object used as the selection key | Optional, defaults to primary key of  defaults to the child if not specified |

##### One-to-One Associations

When defining an association property for a one-to-one (1:1) association, the associated schema component can be included as a property of the object being returned.

In the Chinook database, an example of this type of association can be found in the `invoice` table, where the `customer_id` serves as a foreign key referencing the customer record.

In the schema component object model, this relationship can be specified, allowing the resultant invoice objects to have a `customer` property containing a customer object.


Here's an example of how the `customer` property would be specified in the `invoice` schema component object;


    invoice:
      type: object
      x-am-engine: postgres
      x-am-database: chinook
      properties:
        invoice_id:
          type: integer
          x-am-primary-key: auto
        customer_id:
          type: integer
        customer:
          x-am-type: relation
          x-am-schema-object: customer
          x-am-parent-property: customer_id

In this example the `customer` property type is specified as being a relation to the schema component object `customer'.  When fetching data API-Make will then use 

With API-Maker 

| Attribute | | Description |
|-----------|-|-------------|
| x-am-schema | Required | The name of the schema component object to use as the source of the relation. |
| x-am-cardinality | Optional | Can be either single or multiple, defaults to single |
| x-am-parent-property | Required | The name of the sibling property to use as the selection key in the relation |
| x-am-child-property | Optional | 

# Services

For annotated compoenent schema objects API-Make provides RESTful services supporting the full CRUD based record lifecycle.

When interacting with these services there are three catagories of data being supplied in the request.  These catagories are;

**Query Parameters** - These parameters are generally passed in the request query string or path parameters.  With query string values relational expressions can be applied to filter sets of records.  These parameters can be applied to GET, PUT, and DELETE methods.

Fundanmental relational expressions are supported when selecting records using a query string.  When passing a query string parameter the value can be prefixed with an relational operator separated by a ':'.  For example a parameter of 'laditude=lt:30' would select records those records with a laditude of less than 30. The supported operations are lt, le, eq, ne, ge, gt, in, between, not-in, not-between. 

**Store Parameters** - These parameters are always passed in the request body in JSON format and represent data to be stored.  These parameters are only accepted only by POST and PUT methods.

**Metadata Parameters** - These parameters are alway passed via the request query string and are used to supply directives for processing the request.  The names of these parameters are always prefixed with an '_'.

| Name | Methods | Description |
|------|---------|-------------|
| _count | GET   | Returns the count of records selected. |
| _properties | GET | Allows tailoring the output results.  |
| _case | GET | Return the results properties in camel case |



| Operation | Method | Description |
|-----------|--------|-------------|
| Query     | GET    | Query and Metadata parameters are passed via either path parmeters or the query string. |
| Create    | POST   | Values to be stored are passed in the request body in JSON format. |
| Update    | PUT    | Values to be stored are passed in the request body in JSON format. Query and Metadata parameters for record selection are passed via either path parmeters or the query string. |
| Delete   | DELETE | Query and Metadata parameters are passed via either path parmeters or the query string. |

## GET - Record Selection

## POST - Record Creation

## PUT - Record Modification

## DELETE - Record Deletion

