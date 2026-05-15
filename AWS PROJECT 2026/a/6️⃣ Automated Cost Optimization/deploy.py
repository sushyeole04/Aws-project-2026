import boto3
import json
import zipfile
import os
import time

def create_lambda_deployment_package():
    print("Creating Lambda deployment package...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lambda_path = os.path.join(script_dir, 'lambda_function.py')
    zip_path = os.path.join(script_dir, 'function.zip')
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(lambda_path, 'lambda_function.py')
    print("Deployment package created.")
    return zip_path

def deploy_infrastructure():
    iam = boto3.client('iam')
    aws_lambda = boto3.client('lambda')
    events = boto3.client('events')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    
    role_name = 'CostOptimizationLambdaRole'
    lambda_function_name = 'CostOptimizerFunction'
    rule_name = 'CostOptimizerSchedule'
    
    # 1. Create IAM Role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    print(f"Creating IAM Role: {role_name}...")
    try:
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        role_arn = response['Role']['Arn']
        print(f"Role created successfully. ARN: {role_arn}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"Role {role_name} already exists. Fetching ARN...")
        role_arn = iam.get_role(RoleName=role_name)['Role']['Arn']

    # 2. Attach Policies to Role
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:DescribeInstances",
                    "ec2:StopInstances",
                    "cloudwatch:GetMetricStatistics",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "*"
            }
        ]
    }
    
    print("Attaching inline policy to role...")
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName='CostOptimizationPolicy',
        PolicyDocument=json.dumps(policy_document)
    )
    
    # Wait for role to propagate
    print("Waiting 15 seconds for IAM role to propagate...")
    time.sleep(15)
    
    # 3. Create Lambda Function
    zip_path = create_lambda_deployment_package()
    
    print(f"Deploying Lambda function: {lambda_function_name}...")
    with open(zip_path, 'rb') as f:
        zipped_code = f.read()
        
    try:
        response = aws_lambda.create_function(
            FunctionName=lambda_function_name,
            Runtime='python3.9',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zipped_code},
            Timeout=60,
            MemorySize=128
        )
        lambda_arn = response['FunctionArn']
        print("Lambda function created successfully.")
    except aws_lambda.exceptions.ResourceConflictException:
        print(f"Function {lambda_function_name} already exists. Updating code...")
        response = aws_lambda.update_function_code(
            FunctionName=lambda_function_name,
            ZipFile=zipped_code
        )
        lambda_arn = aws_lambda.get_function(FunctionName=lambda_function_name)['Configuration']['FunctionArn']
        print("Lambda function code updated.")
        
    # 4. Create EventBridge Rule
    print(f"Creating EventBridge Rule: {rule_name}...")
    try:
        response = events.put_rule(
            Name=rule_name,
            ScheduleExpression='rate(15 minutes)',
            State='ENABLED',
            Description='Triggers Lambda every 15 minutes to optimize EC2 costs'
        )
        rule_arn = response['RuleArn']
        print("EventBridge Rule created successfully.")
    except Exception as e:
        print(f"Error creating rule: {e}")
        return
        
    # 5. Add Lambda permission for EventBridge
    print("Adding permission for EventBridge to invoke Lambda...")
    try:
        aws_lambda.add_permission(
            FunctionName=lambda_function_name,
            StatementId='EventBridgeInvokeLambda',
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=rule_arn
        )
        print("Permission added successfully.")
    except aws_lambda.exceptions.ResourceConflictException:
        print("Permission already exists.")
        
    # 6. Add Lambda as target for EventBridge Rule
    print("Adding Lambda as target to EventBridge Rule...")
    try:
        events.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': lambda_arn
                }
            ]
        )
        print("Target added successfully.")
    except Exception as e:
        print(f"Error adding target: {e}")
        return
        
    print("\n[SUCCESS] Deployment Complete!")
    print(f"Lambda ARN: {lambda_arn}")
    print("The system will now run every 15 minutes to stop idle EC2 instances tagged with AutoStop=True.")

if __name__ == "__main__":
    deploy_infrastructure()
