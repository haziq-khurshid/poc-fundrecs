# poc-fundrecs — Real-Time CDC Data Pipeline

A proof-of-concept real-time Change Data Capture (CDC) pipeline built on AWS managed services. Captures database changes from PostgreSQL in real-time, enriches and transforms them via Lambda, and makes them immediately queryable via Athena — all without managing any streaming infrastructure.

---

## Architecture

```
┌─────────────────┐     CDC (logical      ┌─────────────┐
│  Amazon RDS     │     replication)      │  AWS DMS    │
│  PostgreSQL     │ ─────────────────────▶│  Migration  │
│  (source DB)    │                       │  Task       │
└─────────────────┘                       └──────┬──────┘
                                                 │ streams records
                                                 ▼
                                        ┌─────────────────┐
                                        │  Kinesis Data   │
                                        │  Streams        │
                                        └────────┬────────┘
                                                 │ triggers on new records
                                                 ▼
                              ┌──────────────────────────────────┐
                              │         AWS Lambda               │
                              │  - Decodes Kinesis records       │
                              │  - Joins with static product     │
                              │    data from S3                  │
                              │  - Calculates total_price        │
                              │  - Routes by product category    │
                              └──────────────┬───────────────────┘
                                             │ writes CSV partitions
                                             ▼
                                    ┌────────────────┐
                                    │   Amazon S3    │
                                    │  (data lake)   │
                                    │  cdc-transformed/
                                    │  ├── customers/│
                                    │  ├── electronics/
                                    │  └── clothing/ │
                                    └───────┬────────┘
                                            │ queried by
                                            ▼
                                    ┌────────────────┐
                                    │ Amazon Athena  │
                                    │ (ad-hoc SQL    │
                                    │  analytics)    │
                                    └────────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Source Database | Amazon RDS (PostgreSQL) |
| CDC Mechanism | PostgreSQL logical replication (`pgoutput`) |
| CDC Capture & Delivery | AWS DMS (Database Migration Service) |
| Streaming | Amazon Kinesis Data Streams |
| Transformation | AWS Lambda (Python 3.x) |
| Static Data Store | Amazon S3 (JSON) |
| Data Lake | Amazon S3 (CSV partitioned by category/timestamp) |
| Analytics | Amazon Athena |
| Secrets Management | AWS Secrets Manager |

---

## How It Works

### 1. CDC at the Source
PostgreSQL is configured with `wal_level=logical`, enabling logical replication. A replication slot (`fundrecs_slot` using `pgoutput`) tracks every INSERT, UPDATE, and DELETE on the `orders` and `customers` tables.

### 2. DMS Captures and Streams Changes
AWS DMS reads from the replication slot and forwards each change event as a structured JSON record into Kinesis Data Streams. The DMS task runs in **"Migrate existing data and replicate ongoing changes"** mode — so it handles both initial load and ongoing CDC.

### 3. Lambda Transforms in Real-Time
Each Kinesis record triggers a Lambda invocation. The Lambda:
- Decodes the base64-encoded Kinesis payload
- Skips DMS control records (metadata-only events)
- Routes by `table-name` (`orders` vs `customers`)
- For orders: joins against static product data loaded from S3, computes `total_price = price × quantity`, and routes the enriched record into a category-keyed bucket
- Writes partitioned CSVs to S3 under `cdc-transformed/{category}/{timestamp}.csv`

### 4. Athena for Analytics
Athena tables sit on top of the S3 partitions. Once Lambda writes new files, they are immediately queryable — no ETL jobs, no loading step.

---

## Key Technical Decisions

**Why DMS + Kinesis instead of Debezium/Kafka?**
For a POC focused on AWS-native infrastructure, DMS removes the need to self-manage a Kafka cluster. Kinesis provides similar streaming semantics (ordered, durable, replay-capable) with zero ops overhead. In a production system at scale, a managed Kafka (Confluent or MSK) would offer more flexibility for multi-consumer fan-out.

**Why static product data in S3 instead of a database lookup?**
Lambda cold-start latency and connection pooling constraints make direct DB lookups per-record expensive. Loading product data once per Lambda invocation (warm container reuse) and holding it in memory for the batch is far more efficient. The product catalogue is small and changes infrequently — S3 is the right fit.

**Why CSV output partitioned by category?**
Athena performs best when data is partitioned to allow partition pruning. Routing orders by product category at write-time means category-filtered queries in Athena skip irrelevant S3 objects entirely. The trade-off is slightly more complex Lambda routing logic, which is minimal.

**Why `pgoutput` replication plugin?**
`pgoutput` is the native PostgreSQL logical decoding plugin — no external extensions needed. DMS supports it directly, keeping the RDS setup standard and compatible with future PostgreSQL upgrades.

---

## Setup & Running Locally

### Prerequisites
- AWS account with appropriate IAM permissions
- AWS CLI configured
- PostgreSQL client (psql)

### Step 1 — RDS Setup
1. Create an RDS PostgreSQL instance
2. Store credentials in AWS Secrets Manager
3. Open security group inbound rules to allow local machine access

### Step 2 — Enable CDC on RDS
```sql
-- Verify WAL level (must be 'logical')
SHOW wal_level;

-- Create logical replication slot
SELECT * FROM pg_create_logical_replication_slot('fundrecs_slot', 'pgoutput');

-- Verify slot creation
SELECT * FROM pg_replication_slots;
```

If `wal_level` is not `logical`: create a custom RDS parameter group, set `rds.logical_replication=1`, attach it to the instance, and reboot.

### Step 3 — Create Schema & Seed Data
```bash
psql -h <rds-endpoint> -U <user> -d <db> -f schema.sql
```

### Step 4 — Upload Static Data
```bash
aws s3 cp product_details.json s3://poc-fundrecs/static-data/product_details.json
```

### Step 5 — Deploy DMS
1. Create a DMS replication instance in the same VPC as RDS
2. Create source endpoint pointing to RDS (use Secrets Manager for credentials)
3. Create a Kinesis Data Stream
4. Create target endpoint pointing to Kinesis
5. Create migration task: **"Migrate existing data and replicate ongoing changes"**, map `fundrecs_schema.orders` and `fundrecs_schema.customers`

### Step 6 — Deploy Lambda
1. Create Lambda function with code from `poc-lambda.py`
2. Attach Kinesis trigger pointing to your data stream
3. Grant Lambda IAM permissions: `s3:GetObject`, `s3:PutObject`, `kinesis:GetRecords`

### Step 7 — Configure Athena
Run the SQL in `athena.sql` to create Athena database and external tables over the S3 output prefix.

### Step 8 — End-to-End Test
```sql
-- Insert test records on RDS
INSERT INTO fundrecs_schema.orders (product_id, customer_id, quantity, order_date)
VALUES (1, 101, 3, NOW());
```

Within seconds, the record should appear in Athena via the CDC → DMS → Kinesis → Lambda → S3 → Athena chain.

---

## Project Structure

```
poc-fundrecs/
├── poc-lambda.py        # Lambda transformation function
├── schema.sql           # Source PostgreSQL schema (orders + customers tables)
├── athena.sql           # Athena DDL for querying transformed S3 data
└── product_details.json # Static product reference data (loaded by Lambda from S3)
```
