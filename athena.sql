-- Create DB
CREATE DATABASE IF NOT EXISTS my_cdc_database;

-- Create Customers Table
CREATE EXTERNAL TABLE IF NOT EXISTS my_cdc_database.customers (
    customer_id INT,
    customer_name STRING,
    location STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://poc-fundrecs/cdc-transformed/customers/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- Create Electronics_Orders Table
CREATE EXTERNAL TABLE IF NOT EXISTS my_cdc_database.electronics_orders (
    order_id INT,
    product_id INT,
    customer_id INT,
    quantity INT,
    order_date STRING,
    product_name STRING,
    category STRING,
    price DOUBLE,
    total_price DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://poc-fundrecs/cdc-transformed/electronics/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- Create Furniture_Orders Table
CREATE EXTERNAL TABLE IF NOT EXISTS my_cdc_database.furniture_orders (
    order_id INT,
    product_id INT,
    customer_id INT,
    quantity INT,
    order_date STRING,
    product_name STRING,
    category STRING,
    price DOUBLE,
    total_price DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://poc-fundrecs/cdc-transformed/furniture/'
TBLPROPERTIES ('skip.header.line.count'='1');