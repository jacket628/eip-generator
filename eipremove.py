import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    print("event:",event)
    region = event['region']
    latest_instance_id = event['detail']['EC2InstanceId']
    
    # 创建 EC2 客户端对象
    ec2 = boto3.client('ec2', region_name=region)

    response = ec2.describe_addresses(Filters=[
            {
                'Name': 'instance-id',
                'Values': [latest_instance_id]
            }])
    check = list(response['Addresses'])
    if not check:
        print("Elastic IP does not exist")
    else:
        address = response['Addresses'][0]
        print('AllocationId {} will be released'.format(address['AllocationId']))
        try:
            response = ec2.disassociate_address(AssociationId=address['AssociationId'])
            ec2.delete_tags(
                DryRun=False, Resources=[address['AllocationId']],
                Tags=[{'Key': 'status','Value': 'used'}]
            )    
            ec2.create_tags(
                DryRun=False, Resources=[address['AllocationId']],
                Tags=[{'Key': 'status','Value': 'free'}]
            )
        except Exception as err:
            print(err)
