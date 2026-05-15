import boto3
import json
import logging
import uuid
import urllib.request
import time
from botocore.exceptions import ClientError

# ==========================================
# Configuration
# ==========================================
REGION = 'ap-south-1'
INSTANCE_TYPE = 't3.micro'
PROJECT_TAG = [{'Key': 'Project', 'Value': 'Automation'}]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize boto3 clients using default credential chain
# (e.g., ~/.aws/credentials, environment variables, or IAM role)
ec2_client = boto3.client('ec2', region_name=REGION)
ec2_resource = boto3.resource('ec2', region_name=REGION)
s3_client = boto3.client('s3', region_name=REGION)
iam_client = boto3.client('iam')
ssm_client = boto3.client('ssm', region_name=REGION)

def get_my_ip():
    """Fetches the current public IP address to use as trusted IP for SSH."""
    try:
        ip = urllib.request.urlopen('https://checkip.amazonaws.com', timeout=5).read().decode('utf-8').strip()
        return f"{ip}/32"
    except Exception as e:
        logger.warning(f"Could not automatically detect public IP. Defaulting to 0.0.0.0/0. Error: {e}")
        return "0.0.0.0/0"

def provision_s3():
    """Creates a globally unique S3 bucket with versioning and blocked public access."""
    bucket_name = f"automation-bucket-{uuid.uuid4().hex}"
    try:
        logger.info(f"Creating S3 bucket: {bucket_name} in {REGION}...")
        
        # 1. Create Bucket
        if REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
        
        # 2. Enable Versioning
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # 3. Block Public Access
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
        
        # 4. Add Tags
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': PROJECT_TAG}
        )
        
        logger.info(f"S3 bucket '{bucket_name}' successfully provisioned and secured.")
        return bucket_name
    except ClientError as e:
        logger.error(f"Failed to provision S3 bucket: {e}")
        raise

def create_iam_role_for_ec2(bucket_name):
    """Creates an IAM role and instance profile with least privilege access to the created S3 bucket."""
    role_name = f"AutomationEC2Role-{uuid.uuid4().hex[:8]}"
    profile_name = f"AutomationEC2Profile-{uuid.uuid4().hex[:8]}"
    
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        logger.info(f"Creating IAM Role: {role_name}...")
        # Create Role
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Tags=PROJECT_TAG
        )

        # Attach Least Privilege Policy for S3
        # Allows reading, writing, and listing ONLY on the specific bucket created
        s3_least_privilege_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:DeleteObject"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ]
                }
            ]
        }
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='S3LeastPrivilegePolicy',
            PolicyDocument=json.dumps(s3_least_privilege_policy)
        )

        logger.info(f"Creating Instance Profile: {profile_name}...")
        # Create Instance Profile
        iam_client.create_instance_profile(
            InstanceProfileName=profile_name,
            Tags=PROJECT_TAG
        )
        
        # Attach Role to Profile
        iam_client.add_role_to_instance_profile(
            InstanceProfileName=profile_name,
            RoleName=role_name
        )
        
        # Wait for IAM propagation to ensure profile is ready when EC2 launches
        logger.info("Waiting for IAM role propagation (approx 15 seconds)...")
        time.sleep(15) 
        
        return profile_name
    except ClientError as e:
        logger.error(f"Failed to create IAM role/profile: {e}")
        raise

def get_latest_al2_ami():
    """Fetches the latest Amazon Linux 2 AMI ID for the specified region."""
    try:
        response = ssm_client.get_parameter(
            Name='/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2'
        )
        ami_id = response['Parameter']['Value']
        logger.info(f"Found latest Amazon Linux 2 AMI: {ami_id}")
        return ami_id
    except ClientError as e:
        logger.error(f"Failed to fetch latest AL2 AMI: {e}")
        raise

def create_security_group():
    """Creates a Security Group allowing HTTP from anywhere and SSH from the deployer's IP."""
    sg_name = f"automation-sg-{uuid.uuid4().hex[:8]}"
    try:
        # Get default VPC to launch the SG
        vpcs = ec2_client.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        if not vpcs['Vpcs']:
            raise ValueError("No default VPC found in this region.")
        vpc_id = vpcs['Vpcs'][0]['VpcId']

        logger.info(f"Creating Security Group: {sg_name} in VPC: {vpc_id}...")
        response = ec2_client.create_security_group(
            GroupName=sg_name,
            Description='Security group for automation project',
            VpcId=vpc_id,
            TagSpecifications=[{'ResourceType': 'security-group', 'Tags': PROJECT_TAG}]
        )
        sg_id = response['GroupId']

        trusted_ip = get_my_ip()
        
        # Authorize ingress rules
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': trusted_ip, 'Description': 'SSH from trusted IP'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP from anywhere'}]
                }
            ]
        )
        logger.info(f"Ingress rules added (SSH: {trusted_ip}, HTTP: 0.0.0.0/0)")
        return sg_id
    except ClientError as e:
        logger.error(f"Failed to create security group: {e}")
        raise

def provision_ec2(sg_id, ami_id, profile_name):
    """Launches the EC2 instance and waits for it to become running."""
    try:
        logger.info(f"Launching EC2 instance ({INSTANCE_TYPE}) with AMI {ami_id}...")
        
        # To avoid Immediate IAM propagation errors, we may need a retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                instances = ec2_resource.create_instances(
                    ImageId=ami_id,
                    InstanceType=INSTANCE_TYPE,
                    MinCount=1,
                    MaxCount=1,
                    SecurityGroupIds=[sg_id],
                    IamInstanceProfile={'Name': profile_name},
                    TagSpecifications=[{'ResourceType': 'instance', 'Tags': PROJECT_TAG}]
                )
                break
            except ClientError as e:
                if 'InvalidParameterValue' in str(e) and 'IAM Instance Profile' in str(e):
                    if attempt < max_retries - 1:
                        logger.warning(f"IAM profile not ready, retrying in 10 seconds (Attempt {attempt + 1}/{max_retries})...")
                        time.sleep(10)
                        continue
                raise

        instance = instances[0]
        logger.info(f"Instance {instance.id} launched. Waiting for it to enter 'running' state...")
        
        # Wait until the instance is running
        instance.wait_until_running()
        instance.reload() # Refresh instance attributes to get Public IP
        
        logger.info(f"Instance {instance.id} is now RUNNING.")
        return instance
    except ClientError as e:
        logger.error(f"Failed to provision EC2 instance: {e}")
        raise

def main():
    logger.info("Starting AWS infrastructure provisioning script...")
    print("=" * 60)
    print("🚀 Initiating AWS Resource Deployment")
    print("=" * 60)
    
    try:
        # 1. Provision S3
        bucket_name = provision_s3()

        # 2. Provision IAM
        profile_name = create_iam_role_for_ec2(bucket_name)

        # 3. Network & Security
        sg_id = create_security_group()

        # 4. AMI Selection
        ami_id = get_latest_al2_ami()

        # 5. Provision EC2
        instance = provision_ec2(sg_id, ami_id, profile_name)

        # 6. Output the details
        print("\n" + "=" * 60)
        print("🎉 Infrastructure Provisioning Complete! 🎉")
        print("=" * 60)
        print(f"✅ EC2 Instance ID : {instance.id}")
        print(f"✅ EC2 Public IP   : {instance.public_ip_address}")
        print(f"✅ S3 Bucket Name  : {bucket_name}")
        print(f"✅ IAM Role Profile: {profile_name}")
        print(f"✅ Security Group  : {sg_id}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Deployment failed due to an error: {e}")
        print("\n❌ Deployment failed. Check the logs above for details.")

if __name__ == "__main__":
    main()
