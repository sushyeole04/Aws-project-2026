import boto3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')
    
    # 1. Find all running instances with tag AutoStop=True
    filters = [
        {'Name': 'tag:AutoStop', 'Values': ['True', 'true']},
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
    
    try:
        response = ec2.describe_instances(Filters=filters)
    except Exception as e:
        logger.error(f"Error describing instances: {e}")
        return {"statusCode": 500, "body": str(e)}
        
    instances_to_check = []
    for reservation in response.get('Reservations', []):
        for instance in reservation.get('Instances', []):
            instances_to_check.append(instance['InstanceId'])
            
    if not instances_to_check:
        logger.info("No running instances found with tag AutoStop=True.")
        return {"statusCode": 200, "body": "No instances to check."}
        
    logger.info(f"Found instances to check: {instances_to_check}")
    
    instances_to_stop = []
    
    # 2. Check CPU utilization for each instance over the last 30 minutes
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=30)
    
    for instance_id in instances_to_check:
        try:
            metrics = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300, # 5 minutes data points
                Statistics=['Average']
            )
            
            datapoints = metrics.get('Datapoints', [])
            if datapoints:
                # Calculate the average across all datapoints in the 30-min window
                avg_cpu = sum(dp['Average'] for dp in datapoints) / len(datapoints)
                logger.info(f"Instance {instance_id} average CPU over 30 mins: {avg_cpu:.2f}%")
                if avg_cpu < 10.0:
                    instances_to_stop.append(instance_id)
            else:
                logger.warning(f"No CPU metric datapoints found for instance {instance_id}. It might have been recently launched.")
                
        except Exception as e:
            logger.error(f"Error getting metrics for instance {instance_id}: {e}")
            
    # 3. Stop the idle instances
    if instances_to_stop:
        logger.info(f"Stopping idle instances: {instances_to_stop}")
        try:
            ec2.stop_instances(InstanceIds=instances_to_stop)
            logger.info("Instances stopped successfully.")
            return {"statusCode": 200, "body": f"Stopped instances: {instances_to_stop}"}
        except Exception as e:
            logger.error(f"Error stopping instances: {e}")
            return {"statusCode": 500, "body": str(e)}
    else:
        logger.info("No idle instances found to stop.")
        return {"statusCode": 200, "body": "No instances required stopping."}
