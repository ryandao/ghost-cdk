from aws_cdk import (
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_events as events,
    aws_events_targets as events_targets,
    aws_lambda as lambda_,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    core,
)

class MonitoringStack(core.Stack):
    """Monitor the uptime of the website with a lambda function.
    Send an email to the webmaster if the function fails.
    """

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        # Validated require props.
        required_props_keys = ['MonitoringUrl', 'CanaryFrequency', 'NotificationEmail']
        for k in required_props_keys:
            if k not in props or not props[k]:
                raise ValueError("Required prop %s is not present" % k)

        canary_fn = lambda_.Function(
            self, 'GhostCanaryFn',
            runtime=lambda_.Runtime.PYTHON_3_6,
            code=lambda_.Code.asset('lambda'),
            handler='ghost_canary.handler',
            environment={
                'WebsiteUrl': props['MonitoringUrl']
            }
        )

        rule = events.Rule(
            self, 'CanarySchedule',
            schedule=events.Schedule.rate(core.Duration.seconds(props['CanaryFrequency'])),
        )

        rule.add_target(events_targets.LambdaFunction(canary_fn))

        alarm = cw.Alarm(
            self, 'CanaryAlarm',
            metric=canary_fn.metric('Errors'),
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1,
        )

        alarm_topic = sns.Topic(
            self, 'AlarmTopic',
        )

        alarm_topic.add_subscription(sns_subscriptions.EmailSubscription(
            email_address=props['NotificationEmail'],
        ))

        alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))