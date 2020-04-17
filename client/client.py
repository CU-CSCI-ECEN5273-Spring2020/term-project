#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
client.py
gerhard van andel
"""

import sys
import json
import argparse
import requests

URL = 'localhost:5000'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=URL, type=str, nargs='?', help='controller url')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--target', type=str, help='target url')
    group.add_argument('--uuid', type=str, help='uuid')
    group.add_argument('--stats', action='store_true', default=False, help='stats')
    group.add_argument('--queues', action='store_true', default=False, help='queues')
    args = parser.parse_args()

    try:
        if args.target:
            response = requests.post(f'http://{args.url}/api/url', json={'url': args.target})
        elif args.uuid:
            response = requests.get(f'http://{args.url}/api/url/{args.uuid}')
        elif args.queues:
            response = requests.get(f'http://{args.url}/api/queues')
        else:
            response = requests.get(f'http://{args.url}/api/stats')
    except requests.exceptions.RequestException as err:
        print(err, file=sys.stderr)
        sys.exit(1)

    print(f'{response.request.method} response code is {response.status_code} seconds {response.elapsed.total_seconds()}')
    print(f'{json.dumps(response.json(), indent=2, sort_keys=True)}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
