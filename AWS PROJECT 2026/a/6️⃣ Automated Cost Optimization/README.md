# Automated EC2 Cost Optimization System 💰☁️

This project provides a fully automated, production-ready solution to reduce AWS costs by identifying and stopping idle EC2 instances based on low CPU utilization.

## 🏗️ Architecture Overview

The system uses serverless architecture and native AWS services:
1. **Amazon EventBridge**: Triggers a scheduled event every 15 minutes.
2. **AWS Lambda**: Runs a Python script that assumes an IAM role, scans EC2 instances, and checks CloudWatch metrics.
3. **Amazon CloudWatch**: Provides `CPUUtilization` metrics over a 30-minute window and stores execution logs for the Lambda function.
4. **Amazon EC2**: The target instances. The script only stops instances that have a specific tag (`AutoStop=True`) and an average CPU usage below 10%.

---

## 📁 Project Structure

- `lambda_function.py`: The core business logic that runs on AWS Lambda. It queries EC2 for tagged instances, checks CloudWatch metrics, and stops underutilized instances.
- `deploy.py`: An Infrastructure-as-Code (IaC) deployment script using `boto3`. It provisions the IAM Role, the Lambda Function, and the EventBridge Schedule automatically.
- `create_test_instance.py`: A helper script that launches a free-tier eligible `t3.micro` EC2 instance with the `AutoStop=True` tag for testing purposes.

---

## 🚀 How to Deploy

1. Ensure you have your AWS credentials configured locally (via `aws configure` or environment variables).
2. Install the required Python package:
   ```bash
   pip install boto3
   ```
3. Run the deployment script:
   ```bash
   python deploy.py
   ```
   *The script will create the necessary IAM permissions, package the Lambda function into a ZIP file, deploy it, and set up the 15-minute EventBridge schedule.*

---

## ⚙️ How it Works

Once deployed, you **do not** need to manually run `lambda_function.py`. 
The system runs in the background automatically:

1. Every 15 minutes, EventBridge invokes the Lambda function.
2. The Lambda function searches for all running EC2 instances with the tag **Key**: `AutoStop` and **Value**: `True` (case-insensitive).
3. For each found instance, it queries CloudWatch for the average `CPUUtilization` over the past **30 minutes**.
4. If the average CPU is **below 10.0%**, the Lambda function safely initiates an EC2 Stop command.
5. All actions, including instances checked and instances stopped, are logged to CloudWatch Logs under `/aws/lambda/CostOptimizerFunction`.

---

## 🧪 How to Test

You can manually tag an existing instance in the AWS Console, or use the provided test script:

1. Run the test script:
   ```bash
   python create_test_instance.py
   ```
2. This will launch a `t3.micro` instance with the `AutoStop=True` tag.
3. Leave the instance running and idle.
4. Wait approximately 15-30 minutes for CloudWatch to gather enough data points and for the EventBridge schedule to trigger.
5. Check your EC2 console—the instance should transition to the `Stopped` state!
6. View the logs in **CloudWatch > Log groups > `/aws/lambda/CostOptimizerFunction`** to see the system in action.

---

## 🧹 Clean Up

To avoid any unwanted charges, remember to terminate your test instances when you are done:
1. Go to the EC2 Console.
2. Select your `CostOptimizerTest` instances.
3. Click **Instance state > Terminate instance**.
