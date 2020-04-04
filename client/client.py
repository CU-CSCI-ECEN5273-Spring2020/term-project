#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
client.py
gerhard van andel
"""

import sys
import json
import logging
import argparse
import requests

URL = 'localhost:5000'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s.%(msecs).03dZ %(levelname)s %(process)d [%(name)s:%(threadName)s] %(module)s/%(funcName)s:%(lineno)d: %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=URL, type=str, nargs='?', help='controller url')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--target', type=str, help='target url')
    group.add_argument('--uuid', type=str, help='uuid')
    args = parser.parse_args()

    try:
        if args.target:
            response = requests.post(f'http://{args.url}/api/url', json={'url': args.target})
        else:
            response = requests.get(f'http://{args.url}/api/url/{args.uuid}')
    except requests.exceptions.RequestException as err:
        logger.error(err)
        sys.exit(1)

    logger.info(f'{response.request.method} response code is {response.status_code} seconds {response.elapsed.total_seconds()}')
    print(f'{json.dumps(response.json(), indent=2, sort_keys=True)}')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
