import csv
import boto3
import json
import base64
from io import StringIO
from datetime import datetime, timezone

# Initialize S3 client
s3_client = boto3.client('s3')
s3_bucket = 'poc-fundrecs'
static_data_key = 'static-data/product_details.json'

def load_static_data():
    """
    Load static product details from S3 and return a dictionary
    mapping product_id to product details.
    """
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key=static_data_key)
        static_data = json.loads(response['Body'].read().decode('utf-8'))
        # Return a dictionary with product_id as the key
        return {item['product_id']: item for item in static_data}
    except Exception as e:
        print(f"Error loading static data from S3: {e}")
        raise

def write_csv_to_s3(data, s3_key, headers):
    """
    Convert data to CSV format and write to S3.
    """
    try:
        # Convert list of dictionaries to CSV
        csv_buffer = StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
        
        # Upload the CSV file to S3
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        print(f"Successfully wrote CSV data to S3: {s3_key}")
    except Exception as e:
        print(f"Error writing CSV data to S3: {e}")
        raise

def lambda_handler(event, context):
    """
    Main Lambda function handler. Processes incoming Kinesis records,
    transforms data, and writes the results to S3.
    """
    try:
        # Load static product data from S3
        product_details = load_static_data()
    except Exception as e:
        print(f"Error during static data load: {e}")
        return {'statusCode': 500, 'body': 'Error loading static data'}
    
    # Prepare containers for customer and order data
    customers = []
    orders_by_category = {}
    
    for record in event['Records']:
        try:
            # Decode and parse the Kinesis record
            payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
            data = json.loads(payload)
            
            # Skip control records
            if data['metadata'].get('record-type') == 'control':
                continue
            
            # Ensure 'data' and 'metadata' keys are present
            if 'data' not in data or 'metadata' not in data:
                continue
            
            table_name = data['metadata'].get('table-name')
            
            if table_name == 'orders':
                # Process order data
                product_id = data['data'].get('product_id')
                quantity = data['data'].get('quantity')
                
                if product_id in product_details:
                    product_info = product_details[product_id]
                    # Enrich order data with product details
                    data['data'].update(product_info)
                    
                    # Calculate total price
                    total_price = product_info['price'] * quantity
                    data['data']['total_price'] = total_price
                    
                    # Organize orders by product category
                    category = product_info['category'].lower().replace(" ", "_")
                    if category not in orders_by_category:
                        orders_by_category[category] = []
                    orders_by_category[category].append(data['data'])
            
            elif table_name == 'customers':
                # Collect customer data
                customers.append(data['data'])
        
        except Exception as e:
            print(f"Error processing record: {e}")
            continue
    
    # Create a timestamp for S3 file naming with colons between hour, minute, and second
    timestamp = datetime.now(timezone.utc).strftime('%Y/%m/%d/%H:%M:%S')
    
    # Write customer data to S3 as a CSV file
    if customers:
        s3_key = f"cdc-transformed/customers/{timestamp}.csv"
        write_csv_to_s3(customers, s3_key, headers=["customer_id", "customer_name", "location"])
    
    # Write orders by category to S3 as CSV files
    for category, orders in orders_by_category.items():
        s3_key = f"cdc-transformed/{category}/{timestamp}.csv"
        write_csv_to_s3(orders, s3_key, headers=["order_id", "product_id", "customer_id", "quantity", "order_date", "product_name", "category", "price", "total_price"])
    
    return {'statusCode': 200, 'body': 'Processing complete'}
