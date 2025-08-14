import json
import boto3
import psycopg2
import os
from botocore.exceptions import ClientError

def get_secret(secret_arn, region_name):
    """Retrieve secret from AWS Secrets Manager"""
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_arn)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except ClientError as e:
        raise e

def handler(event, context):
    """Lambda function to initialize PostgreSQL database with PostGIS"""
    
    print(f"Starting database initialization with event: {json.dumps(event)}")
    
    # Get environment variables
    rds_endpoint = os.environ['RDS_ENDPOINT']
    rds_port = os.environ['RDS_PORT']
    db_name = os.environ['DB_NAME']
    db_username = os.environ['DB_USERNAME']
    secret_arn = os.environ['SECRET_ARN']
    region = context.invoked_function_arn.split(':')[3]
    
    try:
        # Get database password from Secrets Manager
        print("Retrieving database credentials from Secrets Manager")
        secret = get_secret(secret_arn, region)
        db_password = secret['password']
        
        # SQL initialization script
        sql_script = """${sql_file_content}"""
        
        # Connect to database
        print(f"Connecting to database at {rds_endpoint}:{rds_port}")
        connection = psycopg2.connect(
            host=rds_endpoint,
            port=rds_port,
            database=db_name,
            user=db_username,
            password=db_password,
            sslmode='require'
        )
        
        # Execute initialization script
        print("Executing database initialization script")
        cursor = connection.cursor()
        cursor.execute(sql_script)
        connection.commit()
        
        # Get PostGIS version to verify installation
        cursor.execute("SELECT PostGIS_Version();")
        postgis_version = cursor.fetchone()[0]
        print(f"PostGIS version: {postgis_version}")
        
        # Verify schemas were created
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('property_data', 'spatial_data', 'audit_logs', 'cache_data')
            ORDER BY schema_name;
        """)
        schemas = [row[0] for row in cursor.fetchall()]
        print(f"Created schemas: {schemas}")
        
        # Verify extensions were installed
        cursor.execute("""
            SELECT extname 
            FROM pg_extension 
            WHERE extname IN ('postgis', 'postgis_topology', 'uuid-ossp', 'pgcrypto', 'hstore')
            ORDER BY extname;
        """)
        extensions = [row[0] for row in cursor.fetchall()]
        print(f"Installed extensions: {extensions}")
        
        # Close connections
        cursor.close()
        connection.close()
        
        print("Database initialization completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Database initialization completed successfully',
                'postgis_version': postgis_version,
                'schemas_created': schemas,
                'extensions_installed': extensions
            })
        }
        
    except psycopg2.Error as e:
        print(f"Database error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Database connection or execution failed',
                'details': str(e)
            })
        }
        
    except ClientError as e:
        print(f"AWS error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'AWS service error',
                'details': str(e)
            })
        }
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Unexpected error during initialization',
                'details': str(e)
            })
        }
