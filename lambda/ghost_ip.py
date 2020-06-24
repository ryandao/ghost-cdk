import json
import boto3

def handler(event, context):
    print('request: {}'.format(json.dumps(event)))
    asg_name = event['ResourceProperties']['AsgName']
    autoscaling_client = boto3.client('autoscaling')
    resp = autoscaling_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])

    # We should only have 1 running instance
    instance_id = resp['AutoScalingGroups'][0]['Instances'][0]['InstanceId']
    ec2_client = boto3.client('ec2')
    resp = ec2_client.describe_instances(
        InstanceIds=[instance_id],
        Filters=[{
            'Name': 'instance-state-name',
            'Values': [
                'running',
            ]
        }],
    )    
    public_ip = resp['Reservations'][0]['Instances'][0]['PublicIpAddress']

    return {
        'Data': {
            'GhostIp': public_ip
        }
    }