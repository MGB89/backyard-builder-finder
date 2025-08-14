import json
import boto3
import psycopg2
import os
import logging
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs_client = boto3.client('sqs')
secretsmanager_client = boto3.client('secretsmanager')
cloudwatch = boto3.client('cloudwatch')

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

def schedule_property_assessments():
    """Schedule property assessments that are due"""
    logger.info("Checking for properties due for assessment")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find properties that need assessment (example: annual assessments)
        query = """
            SELECT p.id, p.property_id, p.address, p.property_type
            FROM property_data.properties p
            LEFT JOIN property_data.assessments a ON p.id = a.property_id 
                AND a.assessment_date > CURRENT_DATE - INTERVAL '365 days'
            WHERE a.id IS NULL  -- No assessment in the last year
            AND p.assessment_status NOT IN ('in_progress', 'under_review')
            LIMIT 100  -- Process in batches
        """
        
        cursor.execute(query)
        properties_due = cursor.fetchall()
        
        sqs_queue_url = os.environ['SQS_QUEUE_URL']
        scheduled_count = 0
        
        for property_record in properties_due:
            property_id, property_code, address, property_type = property_record
            
            # Create assessment message
            message = {
                'messageType': 'scheduled_assessment',
                'propertyId': str(property_id),
                'propertyCode': property_code,
                'address': address,
                'propertyType': property_type,
                'assessmentType': 'annual',
                'priority': 'normal',
                'scheduledDate': datetime.utcnow().isoformat(),
                'dueDate': (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            # Send to SQS
            sqs_client.send_message(
                QueueUrl=sqs_queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'messageType': {
                        'StringValue': 'scheduled_assessment',
                        'DataType': 'String'
                    },
                    'propertyType': {
                        'StringValue': property_type,
                        'DataType': 'String'
                    },
                    'priority': {
                        'StringValue': 'normal',
                        'DataType': 'String'
                    }
                }
            )
            
            # Update property status
            update_query = """
                UPDATE property_data.properties 
                SET assessment_status = 'pending', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            cursor.execute(update_query, (property_id,))
            
            scheduled_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Scheduled {scheduled_count} properties for assessment")
        
        return {
            'status': 'success',
            'scheduledCount': scheduled_count,
            'propertiesProcessed': len(properties_due)
        }
        
    except Exception as e:
        logger.error(f"Error scheduling assessments: {str(e)}")
        raise e

def cleanup_old_records():
    """Cleanup old audit and temporary records"""
    logger.info("Starting cleanup of old records")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cleanup_results = {}
        
        # Cleanup old audit logs (older than 2 years)
        audit_cleanup_query = """
            DELETE FROM audit_logs.property_audit 
            WHERE changed_at < CURRENT_DATE - INTERVAL '2 years'
        """
        cursor.execute(audit_cleanup_query)
        cleanup_results['audit_logs_deleted'] = cursor.rowcount
        
        # Cleanup old system activity logs (older than 1 year)
        activity_cleanup_query = """
            DELETE FROM audit_logs.system_activity 
            WHERE created_at < CURRENT_DATE - INTERVAL '1 year'
        """
        cursor.execute(activity_cleanup_query)
        cleanup_results['activity_logs_deleted'] = cursor.rowcount
        
        # Cleanup old cache data (older than 30 days)
        cache_cleanup_query = """
            DELETE FROM cache_data.property_search_cache 
            WHERE last_updated < CURRENT_DATE - INTERVAL '30 days'
        """
        cursor.execute(cache_cleanup_query)
        cleanup_results['cache_records_deleted'] = cursor.rowcount
        
        # Cleanup old rejected assessments (older than 1 year)
        assessment_cleanup_query = """
            DELETE FROM property_data.assessments 
            WHERE assessment_status = 'rejected' 
            AND created_at < CURRENT_DATE - INTERVAL '1 year'
        """
        cursor.execute(assessment_cleanup_query)
        cleanup_results['rejected_assessments_deleted'] = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Cleanup completed: {cleanup_results}")
        
        return {
            'status': 'success',
            'cleanupResults': cleanup_results
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise e

def update_property_statistics():
    """Update cached property statistics"""
    logger.info("Updating property statistics")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_properties,
                COUNT(CASE WHEN property_type = 'residential' THEN 1 END) as residential_count,
                COUNT(CASE WHEN property_type = 'commercial' THEN 1 END) as commercial_count,
                COUNT(CASE WHEN property_type = 'industrial' THEN 1 END) as industrial_count,
                COUNT(CASE WHEN assessment_status = 'completed' THEN 1 END) as assessed_properties,
                AVG(assessed_value) as avg_assessed_value,
                MAX(assessed_value) as max_assessed_value,
                MIN(assessed_value) as min_assessed_value
            FROM property_data.properties 
            WHERE assessed_value IS NOT NULL
        """
        
        cursor.execute(stats_query)
        stats = cursor.fetchone()
        
        # Send metrics to CloudWatch
        metrics = [
            {
                'MetricName': 'TotalProperties',
                'Value': stats[0],
                'Unit': 'Count'
            },
            {
                'MetricName': 'ResidentialProperties',
                'Value': stats[1],
                'Unit': 'Count'
            },
            {
                'MetricName': 'CommercialProperties',
                'Value': stats[2],
                'Unit': 'Count'
            },
            {
                'MetricName': 'IndustrialProperties',
                'Value': stats[3],
                'Unit': 'Count'
            },
            {
                'MetricName': 'AssessedProperties',
                'Value': stats[4],
                'Unit': 'Count'
            },
            {
                'MetricName': 'AverageAssessedValue',
                'Value': float(stats[5]) if stats[5] else 0,
                'Unit': 'None'
            }
        ]
        
        # Send metrics to CloudWatch
        for metric in metrics:
            cloudwatch.put_metric_data(
                Namespace='PropertyAssessment/Statistics',
                MetricData=[{
                    'MetricName': metric['MetricName'],
                    'Value': metric['Value'],
                    'Unit': metric['Unit'],
                    'Timestamp': datetime.utcnow()
                }]
            )
        
        cursor.close()
        conn.close()
        
        logger.info("Property statistics updated successfully")
        
        return {
            'status': 'success',
            'statistics': {
                'totalProperties': stats[0],
                'residentialCount': stats[1],
                'commercialCount': stats[2],
                'industrialCount': stats[3],
                'assessedProperties': stats[4],
                'avgAssessedValue': float(stats[5]) if stats[5] else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating statistics: {str(e)}")
        raise e

def check_system_health():
    """Check system health and send alerts if needed"""
    logger.info("Checking system health")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        health_issues = []
        
        # Check for stuck assessments
        stuck_query = """
            SELECT COUNT(*) 
            FROM property_data.properties 
            WHERE assessment_status = 'in_progress' 
            AND updated_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
        """
        cursor.execute(stuck_query)
        stuck_count = cursor.fetchone()[0]
        
        if stuck_count > 0:
            health_issues.append(f"{stuck_count} assessments stuck in progress for more than 7 days")
        
        # Check for failed assessments
        failed_query = """
            SELECT COUNT(*) 
            FROM property_data.assessments 
            WHERE assessment_status = 'rejected' 
            AND created_at > CURRENT_DATE - INTERVAL '1 day'
        """
        cursor.execute(failed_query)
        failed_count = cursor.fetchone()[0]
        
        if failed_count > 10:  # Threshold for concern
            health_issues.append(f"{failed_count} assessments failed in the last 24 hours")
        
        # Check database connection performance
        perf_query = "SELECT COUNT(*) FROM property_data.properties"
        start_time = datetime.utcnow()
        cursor.execute(perf_query)
        end_time = datetime.utcnow()
        query_time = (end_time - start_time).total_seconds()
        
        if query_time > 5:  # Slow query threshold
            health_issues.append(f"Database query performance degraded: {query_time:.2f} seconds")
        
        cursor.close()
        conn.close()
        
        # Send CloudWatch metric for health status
        cloudwatch.put_metric_data(
            Namespace='PropertyAssessment/Health',
            MetricData=[{
                'MetricName': 'HealthIssueCount',
                'Value': len(health_issues),
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            }]
        )
        
        if health_issues:
            logger.warning(f"Health issues detected: {health_issues}")
        else:
            logger.info("System health check passed")
        
        return {
            'status': 'success',
            'healthStatus': 'unhealthy' if health_issues else 'healthy',
            'issues': health_issues,
            'queryPerformance': f"{query_time:.2f}s"
        }
        
    except Exception as e:
        logger.error(f"Error during health check: {str(e)}")
        raise e

def handler(event, context):
    """Main Lambda handler for scheduled tasks"""
    
    logger.info(f"Scheduler Lambda invoked with event: {json.dumps(event)}")
    
    try:
        # Determine what task to run based on event or run all tasks
        task = event.get('task', 'all')
        
        results = {}
        
        if task == 'all' or task == 'assessments':
            results['assessments'] = schedule_property_assessments()
        
        if task == 'all' or task == 'cleanup':
            results['cleanup'] = cleanup_old_records()
        
        if task == 'all' or task == 'statistics':
            results['statistics'] = update_property_statistics()
        
        if task == 'all' or task == 'health':
            results['health'] = check_system_health()
        
        logger.info("Scheduled tasks completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Scheduled tasks completed successfully',
                'timestamp': datetime.utcnow().isoformat(),
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in scheduler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Scheduler task failed',
                'details': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }