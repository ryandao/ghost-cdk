from aws_cdk import (
    aws_efs as efs,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_autoscaling as autoscaling,
    aws_autoscaling_hooktargets as autoscaling_hooktargets,
    aws_lambda as lambda_,
    core,
)

from datetime import (
    datetime,
    timedelta,
    timezone
)

class GhostCdkStack(core.Stack):
    """Deploy a Ghost website to AWS via ECS backed by a single EC2 instance"""

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        website_url = props.get('WebsiteUrl')
        
        # The VPC where everything will live in
        vpc = ec2.Vpc(self, 'GhostVpc', max_azs=1)

        # Create an auto scaling group to be used by the ECS cluster
        asg = self.create_asg(vpc)

        # Create the ECS cluster our Ghost website will be in
        cluster = self.create_ecs_cluster(vpc, asg)

        # Create the Ghost ECS service
        ghost_service = self.create_ghost_ecs_service(cluster, website_url)

        # Export the resources so other stacks can reference
        self.output_props = {
            'Asg': asg,
            'Vpc': vpc,
            'Cluster': cluster,
            'EcsService': ghost_service,
        }
    
    def create_asg(self, vpc):
        asg = autoscaling.AutoScalingGroup(
            self, 'SingleInstanceAsg',
            vpc=vpc,
            machine_image=ecs.EcsOptimizedAmi(),
            instance_type=ec2.InstanceType('t2.micro'),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            associate_public_ip_address=True,
            # We only need 1 instance in the ASG
            max_capacity=1,
            desired_capacity=1,
        )

        # Allow ingress traffic to port 80
        security_group = ec2.SecurityGroup(
            self, 'GhostSg',
            vpc=vpc,
        )

        security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
        )

        asg.add_security_group(security_group)
        return asg
    
    def create_ecs_cluster(self, vpc, asg):
        cluster = ecs.Cluster(self, 'GhostCluster', vpc=vpc)
        cluster.add_auto_scaling_group(asg)
        return cluster
    
    def create_ghost_ecs_service(self, cluster, website_url):
        # TODO: Set up persistent storage with EFS once CDK supports this 
        # https://github.com/aws/aws-cdk/issues/6918

        task_definition = ecs.Ec2TaskDefinition(
            self, 'GhostTaskDef',
        )

        environment_variables = {
            'url': website_url
        } if website_url else None

        container = task_definition.add_container(
            'GhostContainer',
            # Change this container version to update Ghost version
            image=ecs.ContainerImage.from_registry('ghost:3.16'),
            memory_limit_mib=256,
            environment=environment_variables,
        )

        port_mapping = ecs.PortMapping(
            container_port=2368, # the Ghost container uses port 2368
            host_port=80,
            protocol=ecs.Protocol.TCP,
        )

        container.add_port_mappings(port_mapping)

        return ecs.Ec2Service(
            self, 'GhostService',
            cluster=cluster,
            task_definition=task_definition,
        )

    @property
    def outputs(self):
        return self.output_props