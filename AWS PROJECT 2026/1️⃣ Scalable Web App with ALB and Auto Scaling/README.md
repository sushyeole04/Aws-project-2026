# 🚀 Scalable Web App with Application Load Balancer and Auto Scaling

This capstone project demonstrates how to build a highly available, fault-tolerant, and scalable web application architecture on AWS. It uses an **Application Load Balancer (ALB)** to distribute traffic and an **Auto Scaling Group (ASG)** to automatically scale compute resources based on demand.

## 🏗️ Architecture Overview

The infrastructure is provisioned completely using **Infrastructure as Code (IaC)** via AWS CloudFormation. 

Here is the working flow of the architecture:
1. **User** sends an HTTP request from a browser.
2. The request reaches the **Application Load Balancer (ALB)**, which acts as the single point of entry.
3. The ALB distributes incoming traffic evenly across multiple **Amazon EC2 instances**.
4. The **Auto Scaling Group (ASG)** monitors the EC2 instances. It ensures a minimum of 2 instances are running. If an instance fails, it automatically replaces it. It also scales out to a maximum of 4 instances during high traffic.
5. All instances are launched within **Public Subnets** across two different **Availability Zones** to guarantee High Availability.

## 🧰 AWS Services Used

*   **Amazon EC2**: Virtual servers hosting the web app (`t3.micro` instance type).
*   **Application Load Balancer (ALB)**: Distributes incoming HTTP traffic across the EC2 instances.
*   **Auto Scaling Group (ASG)**: Automatically adjusts the number of EC2 instances and replaces unhealthy ones.
*   **Amazon VPC & Subnets**: Custom networking for security and isolation.
*   **Security Groups**: Controls inbound and outbound traffic.
*   **AWS CloudFormation**: Used to automate the entire deployment.

## ⚙️ Prerequisites

*   An AWS Account.
*   [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed on your machine.
*   AWS CLI configured with your credentials (`aws configure`).

## 🚀 How to Deploy

You can deploy the entire infrastructure in a few minutes using the provided PowerShell script.

1. Open PowerShell and navigate to the project folder.
2. Run the deployment script:
   ```powershell
   .\deploy.ps1
   ```
3. Wait for the stack to finish creating. Once complete, the script will output the **Load Balancer URL**.

*(Alternatively, you can manually upload `scalable-webapp.yaml` to the AWS CloudFormation Console).*

## 🧪 How to Test

### 1. Test Load Balancing
*   Open the generated **Load Balancer URL** in your web browser.
*   You will see a webpage showing the **Instance ID** and **Availability Zone** that served your request.
*   Refresh the page multiple times. You will notice the Instance ID changing, which proves the ALB is distributing your traffic to different servers.

### 2. Test Auto Scaling & Fault Tolerance
*   Log into the **AWS Management Console** and navigate to the **EC2 Dashboard**.
*   Select one of your running `WebApp-Instance` servers and manually **Terminate** it.
*   Navigate to the **Auto Scaling Groups** dashboard in the console. 
*   Wait a few minutes. The ASG will detect the terminated instance and automatically launch a brand new EC2 instance to replace it and maintain the desired capacity of 2 servers.

## 🧹 Clean Up

To avoid unexpected AWS charges, be sure to delete the infrastructure when you are done testing.

Run the following command in your terminal:
```bash
aws cloudformation delete-stack --stack-name ScalableWebAppStack
```
*(Or delete the stack directly from the CloudFormation AWS Console).*
