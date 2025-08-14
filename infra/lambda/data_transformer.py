import json
import boto3
import psycopg2
import os
import csv
import io
import logging
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
secretsmanager_client = boto3.client('secretsmanager')

def get_secret(secret_arn):
    """Retrieve secret from AWS Secrets Manager"""
    try:
        response = secretsmanager_client.get_secret_value(SecretId=secret_arn)
        return json.loads(response['SecretString'])
    except ClientError as e:
        logger.error(f"Error retrieving secret: {str(e)}")
        raise e

def get_db_connection():
    """Establish database connection"""
    secret_arn = os.environ['SECRET_ARN']
    secret = get_secret(secret_arn)
    
    return psycopg2.connect(
        host=os.environ['RDS_ENDPOINT'],
        port=os.environ['RDS_PORT'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USERNAME'],
        password=secret['password'],
        sslmode='require'
    )

def process_property_csv(bucket, key):
    """Process property data from CSV file"""
    logger.info(f"Processing property CSV: {bucket}/{key}")
    
    try:
        # Download CSV from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        processed_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 since row 1 is header
            try:
                # Validate required fields
                required_fields = ['property_id', 'address', 'city', 'state', 'zip_code', 'county', 'property_type']
                for field in required_fields:
                    if not row.get(field):
                        raise ValueError(f"Missing required field: {field}")
                
                # Insert or update property
                insert_query = """
                    INSERT INTO property_data.properties (
                        property_id, address, city, state, zip_code, county, property_type,
                        lot_size_sqft, building_sqft, year_built, bedrooms, bathrooms,
                        assessed_value, market_value, tax_value, owner_name, parcel_number,
                        legal_description, zoning_classification, school_district
                    ) VALUES (
                        %(property_id)s, %(address)s, %(city)s, %(state)s, %(zip_code)s, %(county)s, %(property_type)s,
                        %(lot_size_sqft)s, %(building_sqft)s, %(year_built)s, %(bedrooms)s, %(bathrooms)s,
                        %(assessed_value)s, %(market_value)s, %(tax_value)s, %(owner_name)s, %(parcel_number)s,
                        %(legal_description)s, %(zoning_classification)s, %(school_district)s
                    ) ON CONFLICT (property_id) DO UPDATE SET
                        address = EXCLUDED.address,
                        city = EXCLUDED.city,
                        state = EXCLUDED.state,
                        zip_code = EXCLUDED.zip_code,
                        county = EXCLUDED.county,
                        property_type = EXCLUDED.property_type,
                        lot_size_sqft = EXCLUDED.lot_size_sqft,
                        building_sqft = EXCLUDED.building_sqft,
                        year_built = EXCLUDED.year_built,
                        bedrooms = EXCLUDED.bedrooms,
                        bathrooms = EXCLUDED.bathrooms,
                        assessed_value = EXCLUDED.assessed_value,
                        market_value = EXCLUDED.market_value,
                        tax_value = EXCLUDED.tax_value,
                        owner_name = EXCLUDED.owner_name,
                        parcel_number = EXCLUDED.parcel_number,
                        legal_description = EXCLUDED.legal_description,
                        zoning_classification = EXCLUDED.zoning_classification,
                        school_district = EXCLUDED.school_district,
                        updated_at = CURRENT_TIMESTAMP
                """
                
                # Prepare data with type conversion
                data = {
                    'property_id': row['property_id'],
                    'address': row['address'],
                    'city': row['city'],
                    'state': row['state'],
                    'zip_code': row['zip_code'],
                    'county': row['county'],
                    'property_type': row['property_type'],
                    'lot_size_sqft': float(row['lot_size_sqft']) if row.get('lot_size_sqft') else None,
                    'building_sqft': float(row['building_sqft']) if row.get('building_sqft') else None,
                    'year_built': int(row['year_built']) if row.get('year_built') else None,
                    'bedrooms': int(row['bedrooms']) if row.get('bedrooms') else None,
                    'bathrooms': float(row['bathrooms']) if row.get('bathrooms') else None,
                    'assessed_value': float(row['assessed_value']) if row.get('assessed_value') else None,
                    'market_value': float(row['market_value']) if row.get('market_value') else None,
                    'tax_value': float(row['tax_value']) if row.get('tax_value') else None,
                    'owner_name': row.get('owner_name'),
                    'parcel_number': row.get('parcel_number'),
                    'legal_description': row.get('legal_description'),
                    'zoning_classification': row.get('zoning_classification'),
                    'school_district': row.get('school_district')
                }
                
                cursor.execute(insert_query, data)
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                error_msg = f"Row {row_num}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue
        
        # Commit transaction
        conn.commit()
        
        # Close connections
        cursor.close()
        conn.close()
        
        # Move processed file to processed folder
        processed_key = key.replace('uploads/', 'processed/')
        s3_client.copy_object(
            Bucket=bucket,
            CopySource={'Bucket': bucket, 'Key': key},
            Key=processed_key
        )
        
        # Delete original file
        s3_client.delete_object(Bucket=bucket, Key=key)
        
        return {
            'status': 'success',
            'processed_count': processed_count,
            'error_count': error_count,
            'errors': errors,
            'processed_file_key': processed_key
        }
        
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        
        # Move failed file to error folder
        try:
            error_key = key.replace('uploads/', 'errors/')
            s3_client.copy_object(
                Bucket=bucket,
                CopySource={'Bucket': bucket, 'Key': key},
                Key=error_key
            )
            s3_client.delete_object(Bucket=bucket, Key=key)
        except:
            pass  # Don't fail if we can't move the file
            
        raise e

def process_assessment_data(data):
    """Process assessment data"""
    logger.info("Processing assessment data")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert assessment record
        insert_query = """
            INSERT INTO property_data.assessments (
                property_id, assessment_date, assessed_by, assessment_type,
                land_value, improvement_value, total_value, assessment_notes,
                methodology_used, comparable_properties
            ) VALUES (
                %(property_id)s, %(assessment_date)s, %(assessed_by)s, %(assessment_type)s,
                %(land_value)s, %(improvement_value)s, %(total_value)s, %(assessment_notes)s,
                %(methodology_used)s, %(comparable_properties)s
            ) RETURNING id
        """
        
        cursor.execute(insert_query, data)
        assessment_id = cursor.fetchone()[0]
        
        # Update property with latest assessment
        update_query = """
            UPDATE property_data.properties 
            SET assessed_value = %(total_value)s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %(property_id)s
        """
        
        cursor.execute(update_query, {
            'total_value': data['total_value'],
            'property_id': data['property_id']
        })
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'status': 'success',
            'assessment_id': str(assessment_id)
        }
        
    except Exception as e:
        logger.error(f"Error processing assessment data: {str(e)}")
        raise e

def handler(event, context):
    """Lambda handler for SQS-triggered data transformation"""
    
    logger.info(f"Processing SQS event: {json.dumps(event)}")
    
    processed_messages = []
    failed_messages = []
    
    try:
        # Process each SQS record
        for record in event.get('Records', []):
            try:
                # Parse message body
                message_body = json.loads(record['body'])
                message_type = message_body.get('messageType')
                
                logger.info(f"Processing message type: {message_type}")
                
                if message_type == 'csv_file_upload':
                    # Process CSV file upload
                    bucket = message_body['bucket']
                    key = message_body['key']
                    
                    result = process_property_csv(bucket, key)
                    
                    processed_messages.append({
                        'messageId': record['messageId'],
                        'messageType': message_type,
                        'status': 'success',
                        'result': result
                    })
                    
                elif message_type == 'assessment_data':
                    # Process assessment data
                    assessment_data = message_body['data']
                    
                    result = process_assessment_data(assessment_data)
                    
                    processed_messages.append({
                        'messageId': record['messageId'],
                        'messageType': message_type,
                        'status': 'success',
                        'result': result
                    })
                    
                elif message_type == 'batch_processing_request':
                    # Process batch processing request
                    batch_type = message_body['batchType']
                    parameters = message_body['parameters']
                    
                    if batch_type == 'property_validation':
                        result = validate_properties(parameters)
                    elif batch_type == 'assessment_calculation':
                        result = calculate_assessments(parameters)
                    else:
                        raise ValueError(f"Unknown batch type: {batch_type}")
                    
                    processed_messages.append({
                        'messageId': record['messageId'],
                        'messageType': message_type,
                        'batchType': batch_type,
                        'status': 'success',
                        'result': result
                    })
                    
                else:
                    raise ValueError(f"Unknown message type: {message_type}")
                    
            except Exception as e:
                logger.error(f"Error processing message {record['messageId']}: {str(e)}")
                failed_messages.append({
                    'messageId': record['messageId'],
                    'error': str(e),
                    'messageBody': record.get('body', '')[:500]  # Truncate for logging
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data transformation completed',
                'processedMessages': len(processed_messages),
                'failedMessages': len(failed_messages),
                'details': {
                    'processed': processed_messages,
                    'failed': failed_messages
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in data transformer: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Unexpected error in data transformer',
                'details': str(e)
            })
        }

def validate_properties(parameters):
    """Validate property data"""
    logger.info("Validating property data")
    
    # Implementation for property validation
    return {
        'status': 'completed',
        'validatedCount': 0,
        'errorCount': 0
    }

def calculate_assessments(parameters):
    """Calculate property assessments"""
    logger.info("Calculating property assessments")
    
    # Implementation for assessment calculation
    return {
        'status': 'completed',
        'calculatedCount': 0,
        'errorCount': 0
    }