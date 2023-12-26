import json
import boto3

def lambda_handler(event, context):
    # 获取自动扩展组名称和 AWS 区域名称
    auto_scaling_group_name = event['detail']['AutoScalingGroupName']
    region = event['region']
    print("event id",event['id'])
    # 创建 EC2 客户端对象
    ec2 = boto3.client('ec2', region_name=region)
    
    # 获取自动扩展组中最新的 EC2 实例 ID
    latest_instance_id = event['detail']['EC2InstanceId']
    print('Allocate IP to Instance: ', latest_instance_id)
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[latest_instance_id])

    
    # EIP优先从池子里分配
    matched = False
    response = ec2.describe_addresses(Filters=[
            {'Name': 'tag:app','Values': ['trade']},
            {'Name': 'tag:status','Values': ['free']}
        ])
    check = list(response['Addresses'])
    if check:
        print("Elastic IP exists!")
        #通过设置不允许覆盖的分配，若发生并发冲突，后来者会分配失败，并继续尝试其他EIP; 成功则立刻退出循环
        for unused in response['Addresses']:
            print("allocate address from pool:",unused['AllocationId'])
            try:
                ec2.associate_address(AllocationId=unused['AllocationId'],InstanceId=latest_instance_id, AllowReassociation=False)
                ec2.delete_tags(
                    DryRun=False, Resources=[unused['AllocationId']],
                    Tags=[{'Key': 'status','Value': 'free'}]
                )    
                ec2.create_tags(
                    DryRun=False, Resources=[unused['AllocationId']],
                    Tags=[{'Key': 'status','Value': 'used'}]
                )
                matched = True
                break
            except Excep as err:
                print(err)
        print("final status:",matched) 
    
    
    # 分配一个新的 EIP 地址
    if not matched:
        allocation = ec2.allocate_address(
            TagSpecifications=[
                {
                    'ResourceType': 'elastic-ip',
                    'Tags': [
                        {'Key': 'app','Value': 'trade'},
                        {'Key': 'status','Value': 'used'}
                    ]
                },
            ]
        )
        eip = allocation['PublicIp']
        # 将 EIP 地址附加到最新的 EC2 实例
        ec2.associate_address(InstanceId=latest_instance_id, PublicIp=eip)
