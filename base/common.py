#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
common.py
gerhard van andel
"""
import logging
import socket
import redis
import hashlib
from time import sleep
from datetime import datetime
from urllib.parse import urlparse


USER_BUCKET = 'term-project'


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s.%(msecs).03dZ %(levelname)s %(process)d [%(name)s:%(threadName)s] %(module)s/%(funcName)s:%(lineno)d: %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)
    return logger


def wait_for_connection(logger: logging.Logger):
    ping_counter = 1
    is_reachable = False
    start_time = datetime.utcnow()
    while is_reachable is False and ping_counter < 10:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(('rabbitmq', 5672))
            is_reachable = True
        except socket.error as e:
            logger.error(f' [*] failed to connect, retry in {ping_counter ** 2} seconds')
            sleep(ping_counter ** 2)
            ping_counter += 1
        sock.close()
    elapsed = (datetime.utcnow() - start_time).total_seconds()
    if is_reachable:
        logger.info(f' [*] connected, startup time took {elapsed} seconds')
    return is_reachable


def make_spider_task(input_url: str, depth: int = 1):
    """
    """
    url_data = urlparse(input_url)
    if url_data.netloc == '' or url_data.scheme == '':
        raise ValueError(f'invalid url {input_url}')
    if len(url_data.geturl()) > 128:
        raise ValueError(f'url length over limit of 128 {input_url}')
    return {
        'type': 'spider',
        'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        'domain': url_data.netloc,
        'scheme': url_data.scheme,
        'path': url_data.path,
        'depth': depth,
        'url': url_data.geturl()
    }


def get_stats_redis():
    return redis.StrictRedis(host='redis', port=6379, db=3)


def get_domain_redis():
    return redis.StrictRedis(host='redis', port=6379, db=2)


def get_job_redis():
    return redis.StrictRedis(host='redis', port=6379, db=1)


def domain_hash(correlation, url):
    return hashlib.sha256('{}:{}'.format(correlation, url).encode('utf-8')).hexdigest()
