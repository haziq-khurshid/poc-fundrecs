-- Database Schema
-- Create the custom schema
CREATE SCHEMA fundrecs_schema;

-- Create orders Table
CREATE TABLE fundrecs_schema.orders (
    order_id SERIAL PRIMARY KEY,
    product_id INT,
    customer_id INT,
    quantity INT,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Populate sample data
INSERT INTO fundrecs_schema.orders (product_id, customer_id, quantity)
VALUES (1, 101, 2), (2, 102, 1), (1, 103, 4), (3, 104, 1),(1, 105, 2),(3, 105, 3);

-- Create customers table
CREATE TABLE fundrecs_schema.customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(255),
    location VARCHAR(255)
);

-- Populate sample data
INSERT INTO fundrecs_schema.customers (customer_id, customer_name, location)
VALUES (101, 'John Doe', 'New York'), 
       (102, 'Jane Smith', 'San Francisco'), 
       (103, 'Emily Johnson', 'Los Angeles'), 
       (104, 'Michael Brown', 'Chicago'),
       (105, 'Alice Williams', 'Boston');