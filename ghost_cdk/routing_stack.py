from aws_cdk import (
    aws_route53 as route53,
    aws_cloudfront as cf,
    aws_lambda as lambda_,
    aws_autoscaling as autoscaling,
    aws_autoscaling_hooktargets as autoscaling_hooktargets,
    aws_cloudformation as cfn,
    aws_iam as iam,
    aws_certificatemanager as acm,
    custom_resources as cr,
    core,
)

import time

class RoutingStack(core.Stack):
    """Set up a domain name pointing to the ECS container IP address.
    Also set up CloudFront with an ACM cert. The routing chain looks like this:

        website-dns -> cf-distro -> website-origin -> ECS IP
    """

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Validated require props.
        required_props_keys = ['CfOriginDomainName', 'Asg', 'HostedZoneName', 'WebsiteDns']
        for k in required_props_keys:
            if k not in props or not props[k]:
                raise ValueError("Required prop %s is not present" % k)

        # Create a custom resource that returns the IP of the host behind the autoscaling group
        asg = props['Asg']
        asg_ip_handler = lambda_.Function(
            self, 'GhostIpHandler',
            runtime=lambda_.Runtime.PYTHON_3_6,
            code=lambda_.Code.asset('lambda'),
            handler='ghost_ip.handler',
        )

        asg_ip_handler.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=['autoscaling:DescribeAutoScalingGroups', 'ec2:DescribeInstances'],
                resources=['*', '*'],
            )
        )

        asg_ip_provider = cr.Provider(
            self, 'GhostIpProvider',
            on_event_handler=asg_ip_handler,
        )

        asg_ip_resource = cfn.CustomResource(
            self, 'GhostIpResource',
            provider=asg_ip_provider,
            properties={
                'AsgName': asg.auto_scaling_group_name,
                'ts': time.time(), # this makes sure the function is invoked for every CFN update
            }
        )

        # Create R53 HZ and cf origin domain
        if 'ExistingHostedZoneId' in props and props['ExistingHostedZoneId']:
            hz = route53.HostedZone.from_hosted_zone_attributes(
                self, 'HostedZone', 
                zone_name=props['HostedZoneName'],
                hosted_zone_id=props['ExistingHostedZoneId'],
            )
        else:
            hz = route53.HostedZone(
                self, 'HostedZone',
                zone_name=props['HostedZoneName']
            )

        origin_rrset = route53.ARecord(
            self, 'OriginRecord',
            target=route53.RecordTarget.from_ip_addresses(asg_ip_resource.get_att_string('GhostIp')),
            record_name=props['CfOriginDomainName'],
            zone=hz,
        )

        # Create a CF distro
        acm_cert = acm.DnsValidatedCertificate(
            self, 'GhostAcmCert',
            hosted_zone=hz,
            domain_name=props['WebsiteDns'],
            region='us-east-1',
        )

        cf_distro = cf.CloudFrontWebDistribution(
            self, 'CfDistro',
            origin_configs=[cf.SourceConfiguration(
                custom_origin_source=cf.CustomOriginConfig(
                    domain_name=props['CfOriginDomainName'],
                    origin_protocol_policy=cf.OriginProtocolPolicy.HTTP_ONLY,
                ),
                behaviors=[cf.Behavior(is_default_behavior=True)],
            )],
            alias_configuration=cf.AliasConfiguration(
                names=[props['WebsiteDns']],
                acm_cert_ref=acm_cert.certificate_arn,
            ),
            default_root_object='',
        )

        # Create the top level website DNS pointing to the CF distro
        ghost_rrset = route53.CnameRecord(
            self, 'GhostDns',
            domain_name=cf_distro.domain_name,
            zone=hz,
            record_name=props['WebsiteDns'],
        )
