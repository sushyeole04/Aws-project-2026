import boto3
import json
import uuid
import logging
from botocore.exceptions import ClientError
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def create_bucket(s3_client, bucket_name, region):
    """Create an S3 bucket in a specified region"""
    try:
        logging.info(f"Creating bucket: {bucket_name} in region: {region}")
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        logging.info(f"Successfully created bucket: {bucket_name}")
        return True
    except ClientError as e:
        logging.error(f"Error creating bucket: {e}")
        return False

def remove_public_access_block(s3_client, bucket_name):
    """Remove public access block for the bucket to allow public read access"""
    try:
        logging.info(f"Removing public access block for bucket: {bucket_name}")
        s3_client.delete_public_access_block(Bucket=bucket_name)
        logging.info("Successfully removed public access block.")
        return True
    except ClientError as e:
        logging.error(f"Error removing public access block: {e}")
        return False

def set_bucket_policy(s3_client, bucket_name):
    """Set bucket policy to allow public read access to all objects"""
    try:
        logging.info(f"Setting public read policy for bucket: {bucket_name}")
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        policy_string = json.dumps(bucket_policy)
        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=policy_string)
        logging.info("Successfully applied bucket policy.")
        return True
    except ClientError as e:
        logging.error(f"Error setting bucket policy: {e}")
        return False

def enable_static_website_hosting(s3_client, bucket_name):
    """Enable static website hosting for the bucket and set documents"""
    try:
        logging.info(f"Enabling static website hosting for bucket: {bucket_name}")
        website_configuration = {
            'ErrorDocument': {'Key': 'error.html'},
            'IndexDocument': {'Suffix': 'index.html'},
        }
        s3_client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration=website_configuration
        )
        logging.info("Successfully enabled static website hosting.")
        return True
    except ClientError as e:
        logging.error(f"Error enabling static website hosting: {e}")
        return False

def upload_file(s3_client, file_path, bucket_name, object_name, content_type):
    """Upload a file to an S3 bucket with proper ContentType"""
    try:
        logging.info(f"Uploading {file_path} to {bucket_name}/{object_name}")
        s3_client.upload_file(
            file_path, 
            bucket_name, 
            object_name,
            ExtraArgs={'ContentType': content_type}
        )
        logging.info(f"Successfully uploaded {file_path}.")
        return True
    except ClientError as e:
        logging.error(f"Error uploading {file_path}: {e}")
        return False

def main():
    region = 'ap-south-1'
    # Generate a globally unique bucket name
    unique_id = str(uuid.uuid4())[:8]
    bucket_name = f"my-static-website-{unique_id}"
    
    # Initialize boto3 S3 client
    try:
        s3_client = boto3.client('s3', region_name=region)
    except Exception as e:
        logging.error(f"Failed to initialize boto3 client. Check your AWS credentials. Error: {e}")
        sys.exit(1)
        
    logging.info("Starting automated S3 static website deployment...")
    
    # Step 1: Create bucket
    if not create_bucket(s3_client, bucket_name, region):
        sys.exit(1)
        
    # Step 2: Remove Public Access Block
    if not remove_public_access_block(s3_client, bucket_name):
        sys.exit(1)
        
    # Step 3: Set Bucket Policy
    if not set_bucket_policy(s3_client, bucket_name):
        sys.exit(1)
        
    # Step 4: Enable Website Hosting
    if not enable_static_website_hosting(s3_client, bucket_name):
        sys.exit(1)
        
    # Step 5: Upload Files
    # Assuming script is run from the same directory as the HTML files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    files_to_upload = [
        {'filename': 'index.html', 'key': 'index.html', 'content_type': 'text/html'},
        {'filename': 'error.html', 'key': 'error.html', 'content_type': 'text/html'}
    ]
    
    all_uploads_successful = True
    for file_info in files_to_upload:
        file_path = os.path.join(script_dir, file_info['filename'])
        if os.path.exists(file_path):
            success = upload_file(
                s3_client, 
                file_path, 
                bucket_name, 
                file_info['key'], 
                file_info['content_type']
            )
            if not success:
                all_uploads_successful = False
        else:
            logging.warning(f"File {file_path} not found. Skipping upload.")
            all_uploads_successful = False
            
    if not all_uploads_successful:
        logging.warning("Some files were not uploaded successfully. The website might not function perfectly.")

    # Step 6: Output Website URL
    website_url = f"http://{bucket_name}.s3-website.{region}.amazonaws.com"
    logging.info("=========================================")
    logging.info("Deployment Successful! 🚀")
    logging.info(f"S3 Website Endpoint URL: {website_url}")
    logging.info("=========================================")

if __name__ == '__main__':
    main()
