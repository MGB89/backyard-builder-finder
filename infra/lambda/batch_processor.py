import json
import boto3
import os
import logging
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
secretsmanager_client = boto3.client('secretsmanager')

def get_secret(secret_arn):
    """Retrieve secret from AWS Secrets Manager"""
    try:
        response = secretsmanager_client.get_secret_value(SecretId=secret_arn)
        return json.loads(response['SecretString'])
    except ClientError as e:
        logger.error(f"Error retrieving secret: {str(e)}")
        raise e

def process_s3_event(event, context):
    """Process S3 object creation events"""
    
    logger.info(f"Processing S3 event: {json.dumps(event)}")
    
    # Get environment variables
    sqs_queue_url = os.environ['SQS_QUEUE_URL']
    s3_bucket = os.environ['S3_BUCKET']
    
    processed_files = []
    
    try:
        # Process each S3 record
        for record in event.get('Records', []):
            if record.get('eventSource') == 'aws:s3':
                bucket_name = record['s3']['bucket']['name']
                object_key = record['s3']['object']['key']
                event_name = record['eventName']
                
                logger.info(f"Processing {event_name} for {bucket_name}/{object_key}")
                
                # Check if it's a CSV file in the uploads directory
                if object_key.startswith('uploads/') and object_key.endswith('.csv'):
                    
                    # Get object metadata
                    try:
                        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
                        file_size = response['ContentLength']
                        last_modified = response['LastModified'].isoformat()
                        
                        # Create processing message
                        message = {
                            'messageType': 'csv_file_upload',
                            'bucket': bucket_name,
                            'key': object_key,
                            'fileSize': file_size,
                            'lastModified': last_modified,
                            'eventName': event_name,
                            'timestamp': datetime.utcnow().isoformat(),
                            'processingStatus': 'pending'
                        }
                        
                        # Send message to SQS for processing
                        sqs_response = sqs_client.send_message(
                            QueueUrl=sqs_queue_url,
                            MessageBody=json.dumps(message),
                            MessageAttributes={
                                'fileType': {
                                    'StringValue': 'csv',
                                    'DataType': 'String'
                                },
                                'bucket': {
                                    'StringValue': bucket_name,
                                    'DataType': 'String'
                                },
                                'priority': {
                                    'StringValue': 'normal',
                                    'DataType': 'String'
                                }
                            }
                        )
                        
                        logger.info(f"Sent message to SQS: {sqs_response['MessageId']}")
                        
                        processed_files.append({
                            'bucket': bucket_name,
                            'key': object_key,
                            'status': 'queued_for_processing',
                            'messageId': sqs_response['MessageId']
                        })
                        
                    except ClientError as e:
                        logger.error(f"Error processing {object_key}: {str(e)}")
                        processed_files.append({
                            'bucket': bucket_name,
                            'key': object_key,
                            'status': 'error',
                            'error': str(e)
                        })
                        
                else:
                    logger.info(f"Skipping {object_key} - not a CSV file in uploads directory")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'S3 event processed successfully',
                'processedFiles': processed_files,
                'totalFiles': len(processed_files)
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing S3 event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process S3 event',
                'details': str(e)
            })
        }

def process_batch_request(event, context):
    """Process batch processing requests via ALB"""
    
    logger.info(f"Processing batch request: {json.dumps(event)}")
    
    try:
        # Parse request body
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
            
        batch_type = body.get('batchType', 'unknown')
        parameters = body.get('parameters', {})
        
        # Get environment variables
        sqs_queue_url = os.environ['SQS_QUEUE_URL']
        
        # Create batch processing message
        message = {
            'messageType': 'batch_processing_request',
            'batchType': batch_type,
            'parameters': parameters,
            'requestId': context.aws_request_id,
            'timestamp': datetime.utcnow().isoformat(),
            'processingStatus': 'pending'
        }
        
        # Determine priority based on batch type
        priority = 'high' if batch_type in ['urgent_assessment', 'emergency_update'] else 'normal'
        
        # Send to appropriate queue based on priority
        queue_url = os.environ.get('SQS_HIGH_PRIORITY_QUEUE_URL', sqs_queue_url) if priority == 'high' else sqs_queue_url
        
        sqs_response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
            MessageAttributes={
                'batchType': {
                    'StringValue': batch_type,
                    'DataType': 'String'
                },
                'priority': {
                    'StringValue': priority,
                    'DataType': 'String'
                },
                'requestId': {
                    'StringValue': context.aws_request_id,
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Batch request queued: {sqs_response['MessageId']}")
        
        # ALB response format
        return {
            'statusCode': 202,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Batch processing request accepted',
                'requestId': context.aws_request_id,
                'messageId': sqs_response['MessageId'],
                'batchType': batch_type,
                'priority': priority,
                'estimatedProcessingTime': get_estimated_processing_time(batch_type)
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing batch request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to process batch request',
                'details': str(e),
                'requestId': context.aws_request_id
            })
        }

def get_estimated_processing_time(batch_type):
    """Get estimated processing time based on batch type"""
    estimates = {
        'property_import': '5-15 minutes',
        'assessment_calculation': '10-30 minutes',
        'spatial_analysis': '15-45 minutes',
        'report_generation': '2-10 minutes',
        'urgent_assessment': '1-5 minutes',
        'emergency_update': '1-3 minutes',
        'default': '5-20 minutes'
    }
    return estimates.get(batch_type, estimates['default'])

def handler(event, context):
    """Main Lambda handler - routes based on event source"""
    
    logger.info(f"Lambda invoked with event: {json.dumps(event)[:1000]}...")  # Truncate for logging
    
    try:
        # Determine event source and route accordingly
        if 'Records' in event:
            # Check if it's an S3 event
            for record in event['Records']:
                if record.get('eventSource') == 'aws:s3':
                    return process_s3_event(event, context)
                    
        elif 'requestContext' in event:
            # ALB/API Gateway event
            return process_batch_request(event, context)
            
        else:
            # Direct invocation
            return process_batch_request(event, context)
            
    except Exception as e:
        logger.error(f"Unexpected error in handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Unexpected error in batch processor',
                'details': str(e)
            })
        }
