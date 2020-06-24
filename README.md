# Ghost CDK

This CDK project provides a cost-effective way to deploy a Ghost website to AWS using Elastic Container Service (ECS). It also provides optional routing and monitoring setup for the website using Route53, CloudFront, and CloudWatch.

## Getting started

Make sure you have [CDK](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html) installed and follow the guide to configure CDK for your AWS account. This project is set up like a standard Python project.  The initialization process also creates a virtualenv within this project, stored under the .env directory.  To create the virtualenv it assumes that there is a `python3` (or `python` for Windows) executable in your path with access to the `venv` package. If for any reason the automatic creation of the virtualenv fails, you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .env
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .env/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

You can deploy all the CDK stacks in the project 

```
$ cdk deploy "*"
```

Or just the core ECS stack without routing and monitoring setup.

```
$ cdk deploy ghost-cdk
```

## How it works?

The idea is simple - deploy the [Ghost Docker image](https://hub.docker.com/_/ghost) to ECS. To make it cost-effective, we use a single EC2 nano instance to house the container. The routing stack is optional but highly recommended. It sets up CloudFront in front of the ECS service so that hot contents can be cached to reduce the load to the EC2 instance. The monitoring stack creates a Lambda function that verifies the website's uptime and alarms via email notification if the site is down.

## Important: Persistent storage

Currently CDK doesn't support defining a persistent storage for ECS containers. You should set up persistent storage manually. I recommend using EFS ([guide here](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/tutorial-efs-volumes.html)) since it's the most cost-effective option. You can choose to use RDS or Docker data volume as well.

## What if the EC2 instance goes down?

EC2 nano instances don't have good uptime SLA. If the instance is somehow terminated, the autoscaling group will create a new one and ECS will take care of deploying the container to it. If you set up the monitoring stack, you should get an email notification that your website is unavailable. Simply run `cdk deploy ghost-routing` again to wire up the new EC2 instance.

