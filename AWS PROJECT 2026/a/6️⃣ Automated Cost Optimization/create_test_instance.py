import boto3

def create_test_instance():
    ec2 = boto3.client('ec2')
    ssm = boto3.client('ssm')
    
    print("Fetching the latest Amazon Linux 2023 AMI...")
    try:
        response = ssm.get_parameter(
            Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64'
        )
        ami_id = response['Parameter']['Value']
        print(f"Using AMI ID: {ami_id}")
    except Exception as e:
        print(f"Error fetching AMI: {e}")
        return

    print("Launching a t3.micro test instance...")
    try:
        response = ec2.run_instances(
            ImageId=ami_id,
            InstanceType='t3.micro',
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'CostOptimizerTest'},
                        {'Key': 'AutoStop', 'Value': 'True'}
                    ]
                }
            ]
        )
        
        instance_id = response['Instances'][0]['InstanceId']
        print(f"\n[SUCCESS] Successfully created test instance: {instance_id}")
        print("The instance has been tagged with 'AutoStop=True'.")
        print("The Automated Cost Optimization Lambda will detect this instance, check its CPU, and stop it automatically within the next 15-30 minutes!")
        
    except Exception as e:
        print(f"Error launching instance: {e}")

if __name__ == "__main__":
    create_test_instance()
