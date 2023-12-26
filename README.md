#EIP方案说明
1.	方案概述
功能需求：
处理特定业务的一组机器，需要有固定的公网IP，来满足交易对端的检测需求。
希望IP数量是可扩展的，不要受限；
希望做到完全的自动化，并且可观测。

实现方式：
	一组机器绑定一个弹性伸缩组，可以采用观察者模式监听弹性伸缩组的事件，事件驱动来执行lambda，分别是
	1）EC2 Instance Launch Successful事件->eventbridge->lambda，执行分配EIP。
	2）EC2 Instance Terminate Successful事件->eventbridge->lambda，执行释放EIP。

2.	方案详情
1）	编写lambda
在业务所在的区域，进入lambda服务，使用python 3.9编写2个函数。
函数的执行角色都要添加权限 AmazonEC2FullAccess。

eipadd函数: 负责分配EIP给当前启动的机器。EIP优先从池子里分配，做了并发处理；如果池子里不能分配，那么申请新的EIP并分配给当前机器。
注意：
样例代码生成EIP时候，tag是app，值是trade；搜索的过滤条件也是tag:app，值是trade。可以修改成业务需要的tag。
lambda的超时时间设为2分30秒（分配的实例从 “待处理”到“正在运行”时间较长），可以根据实际情况缩短点。

eipremove函数: 负责释放当前机器的EIP。代码会根据实例ID直接过滤出EIP，并执行释放操作。
注意：
超时时间设为30秒。

2）	Lambda函数挂载触发器。
测试配置autoscaling group，所需容量4，最小容量1，最大容量4。
eipadd函数挂载该autoscaling group的EC2 Instance Launch Successful事件。
eipremove函数挂载该autoscaling group的EC2 Instance Terminate Successful事件。

3）	单元测试
auto scaling group首次配置完毕时，机器逐渐增加到4个，函数自动申请4个指定tag的EIP，EIP界面查看到分配的信息；
运维人员手动关闭4台机器，会随着机器的逐渐关闭，函数自动释放这4个EIP，EIP界面查看到空闲的信息；
auto scaling group根据实际配置，又自动增加机器到4台，EIP不会申请新的，而是从池子里再次分配。
再打开Cloudwatch的日志组，查看/aws/lambda/eipadd 和 /aws/lambda/eipremove，函数执行以上逻辑的日志也是正常的，没有报错信息。

3.	参考资料
弹性伸缩组的事件列表
https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-event-reference.html
分配EIP的python SDK
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/allocate_address.html#
获取EIP列表的python SDK:
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_addresses.html#
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/modify_address_attribute.html

