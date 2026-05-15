import boto3
import json
import time

def setup_aws_pipeline():
    # Configuration - Change these variables as needed
    region = 'ap-south-1'
    project_name = 'NodeAppPipeline'
    github_owner = 'YOUR_GITHUB_OWNER'
    github_repo = 'YOUR_REPO_NAME'
    github_branch = 'main'
    # Important: Create a CodeStar Connection in the AWS Console and paste the ARN here
    codestar_connection_arn = 'YOUR_CODESTAR_CONNECTION_ARN' 
    
    # Boto3 Clients
    s3 = boto3.client('s3', region_name=region)
    iam = boto3.client('iam', region_name=region)
    codebuild = boto3.client('codebuild', region_name=region)
    codedeploy = boto3.client('codedeploy', region_name=region)
    codepipeline = boto3.client('codepipeline', region_name=region)

    bucket_name = f"{project_name.lower()}-artifacts-{int(time.time())}"

    # 1. Create S3 Bucket for Artifacts
    print(f"Creating S3 Bucket: {bucket_name}")
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
    except Exception as e:
        print(f"Error creating S3 bucket: {e}")
        return

    # 2. Create IAM Roles
    print("Creating IAM Roles...")
    
    # CodeBuild Role
    build_role_name = f"{project_name}-CodeBuildRole"
    try:
        build_role = iam.create_role(
            RoleName=build_role_name,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Principal": {"Service": "codebuild.amazonaws.com"}, "Action": "sts:AssumeRole"}]
            })
        )
        build_role_arn = build_role['Role']['Arn']
        # Attach policy to allow CloudWatch Logs and S3 access
        iam.put_role_policy(
            RoleName=build_role_name,
            PolicyName='CodeBuildPolicy',
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "*"},
                    {"Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject", "s3:GetObjectVersion"], "Resource": [f"arn:aws:s3:::{bucket_name}", f"arn:aws:s3:::{bucket_name}/*"]}
                ]
            })
        )
    except iam.exceptions.EntityAlreadyExistsException:
        build_role_arn = iam.get_role(RoleName=build_role_name)['Role']['Arn']

    # CodeDeploy Role
    deploy_role_name = f"{project_name}-CodeDeployRole"
    try:
        deploy_role = iam.create_role(
            RoleName=deploy_role_name,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Principal": {"Service": "codedeploy.amazonaws.com"}, "Action": "sts:AssumeRole"}]
            })
        )
        deploy_role_arn = deploy_role['Role']['Arn']
        iam.attach_role_policy(
            RoleName=deploy_role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole'
        )
    except iam.exceptions.EntityAlreadyExistsException:
        deploy_role_arn = iam.get_role(RoleName=deploy_role_name)['Role']['Arn']

    # CodePipeline Role
    pipeline_role_name = f"{project_name}-CodePipelineRole"
    try:
        pipeline_role = iam.create_role(
            RoleName=pipeline_role_name,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Principal": {"Service": "codepipeline.amazonaws.com"}, "Action": "sts:AssumeRole"}]
            })
        )
        pipeline_role_arn = pipeline_role['Role']['Arn']
        iam.put_role_policy(
            RoleName=pipeline_role_name,
            PolicyName='CodePipelinePolicy',
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": ["codestar-connections:UseConnection"], "Resource": "*"},
                    {"Effect": "Allow", "Action": ["s3:*"], "Resource": [f"arn:aws:s3:::{bucket_name}", f"arn:aws:s3:::{bucket_name}/*"]},
                    {"Effect": "Allow", "Action": ["codebuild:BatchGetBuilds", "codebuild:StartBuild"], "Resource": "*"},
                    {"Effect": "Allow", "Action": ["codedeploy:CreateDeployment", "codedeploy:GetDeployment", "codedeploy:GetApplicationRevision", "codedeploy:GetDeploymentConfig", "codedeploy:RegisterApplicationRevision"], "Resource": "*"}
                ]
            })
        )
    except iam.exceptions.EntityAlreadyExistsException:
        pipeline_role_arn = iam.get_role(RoleName=pipeline_role_name)['Role']['Arn']

    print("Waiting 15 seconds for IAM roles to propagate...")
    time.sleep(15)

    # 3. Create CodeBuild Project
    print("Creating CodeBuild Project...")
    try:
        codebuild.create_project(
            name=f"{project_name}-Build",
            source={'type': 'CODEPIPELINE', 'buildspec': 'buildspec.yml'},
            artifacts={'type': 'CODEPIPELINE'},
            environment={
                'type': 'LINUX_CONTAINER',
                'image': 'aws/codebuild/amazonlinux2-x86_64-standard:4.0',
                'computeType': 'BUILD_GENERAL1_SMALL'
            },
            serviceRole=build_role_arn
        )
    except codebuild.exceptions.ResourceAlreadyExistsException:
        print("CodeBuild project already exists.")

    # 4. Create CodeDeploy Application & Group
    print("Creating CodeDeploy Application and Deployment Group...")
    try:
        codedeploy.create_application(applicationName=f"{project_name}-App", computePlatform='Server')
    except codedeploy.exceptions.ApplicationAlreadyExistsException:
        pass

    try:
        codedeploy.create_deployment_group(
            applicationName=f"{project_name}-App",
            deploymentGroupName=f"{project_name}-DeployGroup",
            serviceRoleArn=deploy_role_arn,
            ec2TagFilters=[{'Key': 'Environment', 'Value': 'Production', 'Type': 'KEY_AND_VALUE'}]
        )
    except codedeploy.exceptions.DeploymentGroupAlreadyExistsException:
        print("CodeDeploy deployment group already exists.")

    # 5. Create CodePipeline
    print("Creating CodePipeline...")
    if codestar_connection_arn == 'YOUR_CODESTAR_CONNECTION_ARN':
        print("Skipping pipeline creation. Please update 'codestar_connection_arn' with your actual ARN to create the pipeline.")
    else:
        try:
            codepipeline.create_pipeline(
                pipeline={
                    'name': project_name,
                    'roleArn': pipeline_role_arn,
                    'artifactStore': {'type': 'S3', 'location': bucket_name},
                    'stages': [
                        {
                            'name': 'Source',
                            'actions': [{
                                'name': 'Source',
                                'actionTypeId': {'category': 'Source', 'owner': 'AWS', 'provider': 'CodeStarSourceConnection', 'version': '1'},
                                'outputArtifacts': [{'name': 'SourceArtifact'}],
                                'configuration': {
                                    'ConnectionArn': codestar_connection_arn,
                                    'FullRepositoryId': f"{github_owner}/{github_repo}",
                                    'BranchName': github_branch
                                },
                                'runOrder': 1
                            }]
                        },
                        {
                            'name': 'Build',
                            'actions': [{
                                'name': 'Build',
                                'actionTypeId': {'category': 'Build', 'owner': 'AWS', 'provider': 'CodeBuild', 'version': '1'},
                                'inputArtifacts': [{'name': 'SourceArtifact'}],
                                'outputArtifacts': [{'name': 'BuildArtifact'}],
                                'configuration': {'ProjectName': f"{project_name}-Build"},
                                'runOrder': 1
                            }]
                        },
                        {
                            'name': 'Deploy',
                            'actions': [{
                                'name': 'Deploy',
                                'actionTypeId': {'category': 'Deploy', 'owner': 'AWS', 'provider': 'CodeDeploy', 'version': '1'},
                                'inputArtifacts': [{'name': 'BuildArtifact'}],
                                'configuration': {
                                    'ApplicationName': f"{project_name}-App",
                                    'DeploymentGroupName': f"{project_name}-DeployGroup"
                                },
                                'runOrder': 1
                            }]
                        }
                    ]
                }
            )
            print("Successfully created CodePipeline!")
        except Exception as e:
            print(f"Error creating CodePipeline: {e}")

if __name__ == "__main__":
    setup_aws_pipeline()
