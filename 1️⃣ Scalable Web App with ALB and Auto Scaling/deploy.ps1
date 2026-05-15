# deploy.ps1
# This script deploys the CloudFormation template for the Scalable Web App

$stackName = "ScalableWebAppStack"
$templateFile = "scalable-webapp.yaml"

Write-Host "Deploying AWS CloudFormation Stack: $stackName" -ForegroundColor Cyan

# Check if AWS CLI is installed
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Host "AWS CLI is not installed or not in PATH. Please install it first." -ForegroundColor Red
    exit
}

# Deploy the stack
Write-Host "Creating/Updating stack. This may take a few minutes..." -ForegroundColor Yellow
aws cloudformation deploy `
    --template-file $templateFile `
    --stack-name $stackName `
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM

if ($LASTEXITCODE -eq 0) {
    Write-Host "Stack deployed successfully!" -ForegroundColor Green
    
    # Retrieve the Load Balancer URL
    Write-Host "Fetching the Load Balancer URL..." -ForegroundColor Cyan
    $output = aws cloudformation describe-stacks --stack-name $stackName --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerURL'].OutputValue" --output text
    
    Write-Host "`n===============================================" -ForegroundColor Green
    Write-Host "🌐 Your Scalable Web App is live at:" -ForegroundColor Yellow
    Write-Host $output -ForegroundColor White
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "Note: It might take a few minutes for the EC2 instances to boot up and the Load Balancer to register them as healthy." -ForegroundColor Gray
} else {
    Write-Host "Stack deployment failed. Check the AWS CloudFormation Console for details." -ForegroundColor Red
}
