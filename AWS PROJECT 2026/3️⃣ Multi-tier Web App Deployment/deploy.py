import boto3
import time
import json
from botocore.exceptions import ClientError
from datetime import datetime

# Configuration
STACK_NAME = 'three-tier-webapp-stack'
TEMPLATE_FILE = 'multi-tier-webapp.yaml'
REGION = 'ap-south-1' # Mumbai region

def get_cf_client():
    return boto3.client('cloudformation', region_name=REGION)

def load_template():
    with open(TEMPLATE_FILE, 'r') as file:
        return file.read()

def deploy_stack():
    client = get_cf_client()
    template_body = load_template()
    
    print(f"Deploying stack '{STACK_NAME}' in region '{REGION}'...")
    
    try:
        response = client.create_stack(
            StackName=STACK_NAME,
            TemplateBody=template_body,
            Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
            OnFailure='ROLLBACK',
            Tags=[{'Key': 'Project', 'Value': '3-Tier-WebApp'}]
        )
        print(f"Stack creation initiated. Stack ID: {response['StackId']}")
        wait_for_completion(client, STACK_NAME)
        print_outputs(client, STACK_NAME)
        
    except ClientError as e:
        if 'AlreadyExistsException' in str(e):
            print(f"Stack '{STACK_NAME}' already exists. Updating...")
            update_stack(client, template_body)
        else:
            print(f"Error creating stack: {e}")

def update_stack(client, template_body):
    try:
        response = client.update_stack(
            StackName=STACK_NAME,
            TemplateBody=template_body,
            Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'],
            Tags=[{'Key': 'Project', 'Value': '3-Tier-WebApp'}]
        )
        print("Stack update initiated...")
        wait_for_completion(client, STACK_NAME)
        print_outputs(client, STACK_NAME)
    except ClientError as e:
        if 'No updates are to be performed' in str(e):
            print("No updates are necessary. Stack is already up to date.")
            print_outputs(client, STACK_NAME)
        else:
            print(f"Error updating stack: {e}")

def wait_for_completion(client, stack_name):
    print("Waiting for stack to complete... (This can take 10-20 minutes depending on RDS)")
    
    while True:
        response = client.describe_stacks(StackName=stack_name)
        status = response['Stacks'][0]['StackStatus']
        
        if status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
            print(f"\nSuccess! Stack reached state: {status}")
            break
        elif status in ['CREATE_FAILED', 'ROLLBACK_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE', 'UPDATE_FAILED']:
            print(f"\nFailed! Stack reached state: {status}")
            print_events(client, stack_name)
            raise Exception(f"Stack deployment failed with status: {status}")
            
        print(".", end="", flush=True)
        time.sleep(15)

def print_events(client, stack_name):
    print("\nRecent Stack Events:")
    try:
        events = client.describe_stack_events(StackName=stack_name)['StackEvents']
        for event in events[:10]: # Print last 10 events
            print(f"[{event.get('Timestamp', '')}] {event.get('ResourceType', '')} - {event.get('ResourceStatus', '')} - {event.get('ResourceStatusReason', '')}")
    except Exception as e:
        print(f"Could not retrieve events: {e}")

def print_outputs(client, stack_name):
    response = client.describe_stacks(StackName=stack_name)
    outputs = response['Stacks'][0].get('Outputs', [])
    
    print("\n" + "="*50)
    print("🚀 DEPLOYMENT OUTPUTS")
    print("="*50)
    
    if not outputs:
        print("No outputs found for this stack.")
    
    for output in outputs:
        key = output['OutputKey']
        value = output['OutputValue']
        desc = output.get('Description', '')
        print(f"{key}: {value}")
        if desc:
            print(f"  └─ {desc}")
    
    print("="*50)

if __name__ == '__main__':
    deploy_stack()
