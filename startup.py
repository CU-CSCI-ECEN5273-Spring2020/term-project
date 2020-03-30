#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
startup.py
gerhard van andel
"""

import argparse
import json
import time
import sys
import os

from googleapiclient.errors import HttpError
import googleapiclient.discovery
import google.auth


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop'])
    parser.add_argument('name', default='term-project', nargs='?', help='project name')
    parser.add_argument('zone', default='us-west1-a', nargs='?', help='zone')
    parser.add_argument('region', default='us-west1', nargs='?', help='region')
    args = parser.parse_args()

    credentials, project = google.auth.default()

    compute = googleapiclient.discovery.build(
        'compute', 'v1', credentials=credentials)

    instance_data = [
        ('redis', 6379, None, None),
        ('rabbitmq', 15672, None, None),
        ('controller', 5000, None, None),
        ('web_bot', 0, None, '0'),
        ('scan_bot', 0, None, '0')
    ]

    for instance in instance_data:
        name = instance[0] + '-' + args.name
        if args.action == "start":
            start(compute, project, name, instance, args)
        elif args.action == "stop":
            stop(compute, project, name, instance, args)

    for i in progressbar(range(180), "- starting instances: ", 40):
        time.sleep(1)

    for instance in list_instances(compute, project, args.zone):
        print('{} - {}'.format(
            instance['name'],
            instance['networkInterfaces'][0]['accessConfigs'][0]['natIP']))


def stop(compute, project, name, instance, args):
    print("Running stop command")
    try:
        if instance[1] is not None:
            remove_firewall_rule(compute, project, name, instance, args)
    except HttpError as err:
        if 'not found' in str(err):
            print("+ firewall rule {} dose not exist, skipping".format(name), file=sys.stderr)

    try:
        delete_instance(compute, project, name, instance, args)
    except HttpError as err:
        if 'not found' in str(err):
            print("+ instance {} dose not exist, skipping".format(name), file=sys.stderr)


def start(compute, project, name, instance, args):
    print("Running start command")
    try:
        if instance[1] != 0:
            add_firewall_rule(compute, project, name, instance, args)
    except HttpError as err:
        if 'already exists' in str(err):
            print("+ firewall rule {} already exists, skipping".format(name), file=sys.stderr)
        else:
            print(err, file=sys.stderr)

    try:
        create_instance(compute, project, name, instance, args)
    except HttpError as err:
        if 'already exists' in str(err):
            print("+ instance {} already exists, skipping".format(name), file=sys.stderr)
        else:
            print(err, file=sys.stderr)


def list_instances(compute, project, zone):
    """
    Get a list of instances
    """
    result = compute.instances().list(project=project, zone=zone).execute()
    if 'items' in result:
        for item in result['items']:
            yield item


def create_instance(compute, project, name, instance, args):
    """
    Get the latest ubuntu 1804 latest image.
    """
    print('- creating instance')
    family = 'ubuntu-1804-lts' if instance[2] is None else instance[2]
    image_response = compute.images().getFromFamily(
        project='ubuntu-os-cloud', family=family).execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    machine_type = "zones/{}/machineTypes/f1-micro".format(args.zone)
    file_path = os.path.join(os.path.dirname(__file__), instance[0], '{}-install.sh'.format(instance[0]))
    with open(file_path, 'r') as f:
        startup_script = f.read()

    config = {
        'name': name if instance[3] is None else '{}-{}'.format(name, instance[3]),
        'machineType': machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [
                {
                    # Startup script is automatically executed by the
                    # instance upon startup.
                    'key': 'startup-script',
                    'value': startup_script
                }
            ]
        },

        # Tags is readable from the instance and allows you to
        # pass network tags
        'tags': {
            'items': []
        }
    }

    if instance[1] != 0:
        config['tags']['items'].append('{}-{}'.format(name, instance[1]))

    return compute.instances().insert(
        project=project,
        zone=args.zone,
        body=config).execute()


def delete_instance(compute, project, name, instance, args):
    """
        Delete instance with name in zone
    """
    print("- removing compute")
    return compute.instances().delete(
        project=project,
        zone=args.zone,
        instance=name).execute()


def add_firewall_rule(compute, project, name, instance, args):
    """
        Add a firewall rule
    """
    print("- adding firewall rule")
    name = '{}-{}'.format(name, instance[1])
    config = {
        "name": name,
        "sourceRanges": [
            "10.138.0.0/20"
        ],
        "allowed": [
            {
                "ports": [
                    "{}".format(instance[1])
                ],
                "IPProtocol": "tcp"
            }
        ],
        "description": "{} firewall rule for port {}".format(name, instance[1])
    }
    return compute.firewalls().insert(
        project=project,
        body=config).execute()


def remove_firewall_rule(compute, project, name, instance, args):
    """
        Remove a firewall rule
    """
    print("- removing firewall rule")
    return compute.firewalls().delete(
        project=project,
        firewall='{}-{}'.format(name, instance[1])).execute()


def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)

    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
