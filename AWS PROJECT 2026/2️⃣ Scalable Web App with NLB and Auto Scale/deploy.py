import boto3
import time
import sys
from botocore.exceptions import ClientError

def deploy_stack(stack_name, template_file):
    cf_client = boto3.client('cloudformation')

    print(f"Deploying AWS CloudFormation Stack: {stack_name}...")

    # Read the template file
    try:
        with open(template_file, 'r') as file:
            template_body = file.read()
    except FileNotFoundError:
        print(f"Error: Could not find template file '{template_file}'")
        sys.exit(1)

    try:
        # Try to create the stack
        print("Creating stack. This may take a few minutes...")
        cf_client.create_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
        )
        
        # Wait for the stack to be created
        waiter = cf_client.get_waiter('stack_create_complete')
        waiter.wait(StackName=stack_name)
        print("Stack created successfully!")

    except ClientError as e:
        error_message = e.response['Error']['Message']
        if 'AlreadyExistsException' in error_message or 'already exists' in error_message:
            # If stack exists, try to update it
            try:
                print("Stack already exists. Attempting to update...")
                cf_client.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
                )
                
                # Wait for the stack to be updated
                waiter = cf_client.get_waiter('stack_update_complete')
                waiter.wait(StackName=stack_name)
                print("Stack updated successfully!")
                
            except ClientError as update_e:
                update_error_message = update_e.response['Error']['Message']
                if 'No updates are to be performed' in update_error_message:
                    print("No updates are necessary for the stack.")
                else:
                    print(f"Error updating stack: {update_error_message}")
                    sys.exit(1)
        else:
            print(f"Error creating stack: {error_message}")
            sys.exit(1)

    # Fetch the outputs
    print("\nFetching the Load Balancer URL...")
    response = cf_client.describe_stacks(StackName=stack_name)
    outputs = response['Stacks'][0].get('Outputs', [])
    
    lb_url = next((output['OutputValue'] for output in outputs if output['OutputKey'] == 'LoadBalancerURL'), None)

    if lb_url:
        print("\n===============================================")
        print("🌐 Your Scalable Web App is live at:")
        print(lb_url)
        print("===============================================")
        print("Note: It might take a few minutes for the EC2 instances to boot up and the Load Balancer to register them as healthy.")
    else:
        print("Could not find the LoadBalancerURL in the stack outputs.")

if __name__ == "__main__":
    STACK_NAME = "ScalableWebAppNLBStack"
    TEMPLATE_FILE = "scalable-webapp-nlb.yaml"
    
    deploy_stack(STACK_NAME, TEMPLATE_FILE)
