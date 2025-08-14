import json
import boto3
import psycopg2
import os
import logging
import random
import string
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secretsmanager = boto3.client('secretsmanager')
rds = boto3.client('rds')

def get_secret_value(secret_arn, stage):
    """Retrieve secret value for a specific stage"""
    try:
        response = secretsmanager.get_secret_value(
            SecretId=secret_arn,
            VersionStage=stage
        )
        return json.loads(response['SecretString'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None
        raise e

def generate_password():
    """Generate a secure random password"""
    # Generate a 32-character password with uppercase, lowercase, digits, and symbols
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(characters) for _ in range(32))
    return password

def test_connection(host, port, database, username, password):
    """Test database connection with given credentials"""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            sslmode='require',
            connect_timeout=10
        )
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return False

def create_version(secret_arn, secret_value):
    """Create a new version of the secret"""
    try:
        response = secretsmanager.put_secret_value(
            SecretId=secret_arn,
            SecretString=json.dumps(secret_value),
            VersionStages=['AWSPENDING']
        )
        return response['VersionId']
    except ClientError as e:
        logger.error(f"Error creating secret version: {str(e)}")
        raise e

def set_secret_version_stage(secret_arn, version_id, stage):
    """Update the stage for a secret version"""
    try:
        secretsmanager.update_secret_version_stage(
            SecretId=secret_arn,
            VersionStage=stage,
            MoveToVersionId=version_id
        )
    except ClientError as e:
        logger.error(f"Error updating secret version stage: {str(e)}")
        raise e

def modify_rds_password(db_instance_identifier, master_username, new_password):
    """Modify RDS master password"""
    try:
        response = rds.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            MasterUserPassword=new_password,
            ApplyImmediately=True
        )
        logger.info(f"RDS password modification initiated for {db_instance_identifier}")
        return response
    except ClientError as e:
        logger.error(f"Error modifying RDS password: {str(e)}")
        raise e

def handler(event, context):
    """Lambda handler for secret rotation"""
    
    logger.info(f"Secret rotation started with event: {json.dumps(event)}")
    
    # Get secret ARN and step from event
    secret_arn = event['SecretId']
    step = event['Step']
    token = event['ClientRequestToken']
    
    logger.info(f"Processing step: {step} for secret: {secret_arn}")
    
    try:
        # Get current secret value
        current_secret = get_secret_value(secret_arn, 'AWSCURRENT')
        if not current_secret:
            raise Exception("Current secret not found")
        
        # Extract connection details
        host = current_secret.get('host', os.environ.get('RDS_ENDPOINT'))\n        port = current_secret.get('port', os.environ.get('RDS_PORT', 5432))\n        database = current_secret.get('database', current_secret.get('dbname', os.environ.get('DB_NAME')))\n        username = current_secret.get('username', current_secret.get('user', os.environ.get('DB_USERNAME')))\n        \n        # Determine DB instance identifier from endpoint\n        db_instance_identifier = host.split('.')[0] if '.' in host else host\n        \n        if step == \"createSecret\":\n            # Check if AWSPENDING version already exists\n            pending_secret = get_secret_value(secret_arn, 'AWSPENDING')\n            if pending_secret:\n                logger.info(\"AWSPENDING version already exists\")\n                return\n            \n            # Generate new password\n            new_password = generate_password()\n            \n            # Create new secret value\n            new_secret = current_secret.copy()\n            new_secret['password'] = new_password\n            \n            # Create AWSPENDING version\n            version_id = create_version(secret_arn, new_secret)\n            logger.info(f\"Created AWSPENDING version: {version_id}\")\n            \n        elif step == \"setSecret\":\n            # Get the pending secret\n            pending_secret = get_secret_value(secret_arn, 'AWSPENDING')\n            if not pending_secret:\n                raise Exception(\"AWSPENDING version not found\")\n            \n            # Update RDS master password\n            new_password = pending_secret['password']\n            modify_rds_password(db_instance_identifier, username, new_password)\n            \n            # Wait for RDS modification to complete\n            import time\n            time.sleep(30)  # Wait for password change to propagate\n            \n            logger.info(\"RDS password updated successfully\")\n            \n        elif step == \"testSecret\":\n            # Get the pending secret\n            pending_secret = get_secret_value(secret_arn, 'AWSPENDING')\n            if not pending_secret:\n                raise Exception(\"AWSPENDING version not found\")\n            \n            # Test connection with new credentials\n            success = test_connection(\n                host=host,\n                port=port,\n                database=database,\n                username=username,\n                password=pending_secret['password']\n            )\n            \n            if not success:\n                raise Exception(\"Connection test failed with new password\")\n            \n            logger.info(\"Connection test successful with new password\")\n            \n        elif step == \"finishSecret\":\n            # Get current and pending versions\n            current_secret = get_secret_value(secret_arn, 'AWSCURRENT')\n            pending_secret = get_secret_value(secret_arn, 'AWSPENDING')\n            \n            if not pending_secret:\n                logger.info(\"AWSPENDING version not found, rotation may already be complete\")\n                return\n            \n            # Get version IDs\n            current_response = secretsmanager.describe_secret(SecretId=secret_arn)\n            \n            current_version_id = None\n            pending_version_id = None\n            \n            for version_id, stages in current_response['VersionIdsToStages'].items():\n                if 'AWSCURRENT' in stages:\n                    current_version_id = version_id\n                elif 'AWSPENDING' in stages:\n                    pending_version_id = version_id\n            \n            if not pending_version_id:\n                raise Exception(\"AWSPENDING version ID not found\")\n            \n            # Move AWSPENDING to AWSCURRENT\n            if current_version_id:\n                # Move current to previous\n                set_secret_version_stage(secret_arn, current_version_id, 'AWSPREVIOUS')\n            \n            # Move pending to current\n            set_secret_version_stage(secret_arn, pending_version_id, 'AWSCURRENT')\n            \n            logger.info(\"Secret rotation completed successfully\")\n            \n        else:\n            raise Exception(f\"Unknown step: {step}\")\n        \n        return {\n            'statusCode': 200,\n            'body': json.dumps({\n                'message': f'Step {step} completed successfully',\n                'secretArn': secret_arn\n            })\n        }\n        \n    except Exception as e:\n        logger.error(f\"Error in step {step}: {str(e)}\")\n        \n        # If this is not the createSecret step, we should fail gracefully\n        if step != \"createSecret\":\n            raise e\n        \n        return {\n            'statusCode': 500,\n            'body': json.dumps({\n                'error': f'Step {step} failed',\n                'details': str(e),\n                'secretArn': secret_arn\n            })\n        }