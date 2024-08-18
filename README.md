# poc-fundrecs
POC - Realtime Data Pipeline with Change Data Capture (CDC)

## Overview:
This POC demonstrates a scalable and real-time data pipeline using AWS-managed services. The pipeline captures Change Data Capture (CDC) events from a PostgreSQL database hosted on Amazon RDS, processes them using AWS DMS, Kinesis Data Streams, and Lambda, and stores the transformed data in S3. The data is then queried using Amazon Athena for real-time analytics.

## Architecture Diagram
![Blank diagram (1)](https://github.com/user-attachments/assets/e57d6dff-b45e-4a9d-af63-c61b8e5adf1f)

## Step by Step guide to setting up the solution
### 1. Setting up Amazon RDS (PostgreSQL) database:
- Create an Amazon RDS database with the PostgreSQL engine.
- Store database credentials in secret in the AWS secrets manager
- Edit inbound rules of the security group to allow access to DB from your local machine
### 2. Enable CDC on database:
**Pre-requisite:** Ensure that the **wal_level** is set to logical for logical replication.
- Create a new parameter group for the RDS database
- In the parameter group, find and **set rds.logical_replication to 1**.
- Attach the newly created parameter group to DB and reboot the DB
- Verify changes using SQL query **"SHOW wal_level;"**, it should return logical instead of minimal
- Create a logical replication slot in your database. This replication slot will be used to track changes.
- Create a logical replication slot:
```SELECT * FROM pg_create_logical_replication_slot('fundrecs_slot', 'pgoutput');```
- Verify the replication slot:
```SELECT * FROM pg_replication_slots;```

### 3. Populate sample data:
#### Schema Overview and Transformation Logic
The source PostgreSQL database consists of two main tables within a custom schema called **fundrecs_schema**:

1- Orders Table:
Purpose: Store details of customer orders.

2- Customers Table:
Purpose: Stores information about customers.

Run the SQL script in the ```schema.sql``` file to set up the initial schema.

### 4. Setup DMS for CDC:
- Create a DMS replication instance (version should be compatible with Postgres version)
- Ensure that you select the same VPC as your RDS instance
- Create a **source endpoint** for RDS
- Create a data stream in Amazon Kinesis to be used as the target for DMS
- Create a **target endpoint** for Kinesis data stream

#### DMS Migration Task
- Create a DMS migration task with a previously created replication instance, source endpoint, and target endpoint
- In migration option: Choose **Migrate existing data and replicate ongoing changes**.
- In table mappings: Map the **orders** and **customers** tables from the source schema (fundrecs_schema) to the target.
- Create migration task by leaving other options as default

**Once the DMS task is running, you can verify the CDC by checking the records from source data into the Kinesis data stream.**

### 5. Upload static data in S3:
- Upload the ```product_details.json``` file in an S3 bucket
- This file contains some product details which we will use in the transformation step by joining with source data

### 6. Setup a Lambda function to perform Transformations:
- Create a lambda function with code available in the ```poc-lambda.py``` file
- Configure a source trigger with Kinesis Data Stream as the source. It will trigger lambda when there are new records in data stream from DMS
- Join source data with static data from S3 and perform calculations to identify **Total Price** of an order
- Categorize data into multiple categories based on product category.
- Store categorized data into target S3 bucket for Analysis

### 7. Query data using Athena:
- Create a DB in Athena and tables based on the transformed data uploaded on S3
- Run the SQL queries from ```athena.sql``` file
- Verify data categorized into separate categories based on product category

### 8. Test end-to-end Pipeline
- In order to test the end to end pipeline, Insert few records in source tables on RDS database
- You should see the new records in Athena tables in real-time




  
 
