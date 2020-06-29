#!/usr/bin/env python3

from aws_cdk import core

from ghost_cdk.ghost_ecs_stack import GhostEcsStack
from ghost_cdk.routing_stack import RoutingStack
from ghost_cdk.monitoring_stack import MonitoringStack

import os
import yaml

# Read configurations
config_file_path = os.path.join(os.path.dirname(__file__), 'ghost_config.yaml')
with open(config_file_path, 'r') as f:
    configs = yaml.safe_load(f)

app = core.App()

ghost_stack = GhostEcsStack(app, "ghost-ecs", configs['Ghost'])

routing_props = ghost_stack.outputs.copy()
routing_props.update(configs['Routing'])
routing_stack = RoutingStack(app, 'ghost-routing', routing_props)

monitoring_stack = MonitoringStack(app, 'ghost-monitoring', configs['Monitoring'])

app.synth()
