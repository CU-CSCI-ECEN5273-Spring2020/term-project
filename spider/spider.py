#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
spider.py
gerhard van andel
"""
import base64
import redis
import pika
import time
import json
import socket
from random import randint
from datetime import datetime
from urllib.robotparser import RobotFileParser
import requests
import logging

from google.cloud import storage


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

# Initialize the Redis connection
uuid_redis = redis.StrictRedis(host='redis', port=6379, db=1)
domain_redis = redis.StrictRedis(host='redis', port=6379, db=2)

# Initialize the rabbitmq connection
credentials = pika.PlainCredentials('guest', 'guest')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
channel = connection.channel()

channel.queue_declare(queue='task_queue', durable=True)
channel.queue_declare(queue='scan_queue', durable=True)

ip_addr = socket.gethostbyname(socket.gethostname())
logger.info(' [*] ip address is: {}'.format(ip_addr))

USER_AGENT = 'asynchronousgillz, 1.1'
USER_DELAY = 10
USER_DEPTH = 1
USER_BUCKET = 'term-project'
MAX_DEPTH = 5
MAX_PULL_COUNT = 20


def string_to_base64(s):
    return base64.b64encode(s.encode('utf-8'))


def base64_to_string(b):
    return base64.b64decode(b).decode('utf-8')


def upload_blob(bucket_name, source_data, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(source_data, content_type='text/html')
    logger.info(' [x] file {} uploaded to {}.'.format(
        destination_blob_name,
        bucket_name))


def check_robots(message):
    """
    Pulls the robots.txt if present
    """
    task = [x for x in message['data'] if x['type'] == 'get'][0]
    url = '{}://{}/robots.txt'.format(task['scheme'], task['domain'])
    logger.info(' [x] {} RobotFileParser {} '.format(message['uuid'], url))
    rp = RobotFileParser(url=url)
    rp.read()
    valid_url = rp.can_fetch('*', message['url'])
    delay = rp.crawl_delay('*')
    domain_data = {
        'domain': task['domain'],
        'valid_url': valid_url,
        'lock': False,
        'crawl_delay': USER_DELAY if delay is None else delay,
        'depth': USER_DEPTH
    }
    domain_redis.set(task['domain'], json.dumps(domain_data))
    logger.info(' [x] {} {} validation results {}'.format(message['uuid'], url, valid_url))
    if not valid_url:
        raise ValueError('robot.txt rule validation failed')
    return domain_data


def pull_data(message, domain_data):
    """
    Pull the html data
    """
    domain = domain_data['domain']
    domain_lock_try_count = 1
    for domain_lock_try_count in range(1, MAX_PULL_COUNT):
        domain_data = json.loads(domain_redis.get(domain))
        if domain_data['lock']:
            sleep_time = (domain_lock_try_count + randint(1, 5)) ** 2
            logger.info(' [x] {} lock unavailable for domain {} retry in {} seconds'.format(message['uuid'], domain_data['domain'], sleep_time))
            time.sleep(sleep_time)
            domain_lock_try_count += 1
        else:
            break
    if domain_lock_try_count >= MAX_PULL_COUNT - 1:
        raise ConnectionError(' [x] {} failed to obtain lock for domain {}'.format(message['uuid'], domain_data['domain']))
    domain_data['lock'] = True
    domain_redis.set(domain, json.dumps(domain_data))
    logger.info(' [x] {} lock acquired for domain {}'.format(message['uuid'], domain_data['domain']))
    response = None
    try:
        logger.info(' [x] {} GET {}'.format(message['uuid'], message['url']))
        response = requests.get(message['url'])
        response.raise_for_status()
    except requests.exceptions.HTTPError() as error:
        logger.error(' [x] {} {} {}'.format(message['uuid'], message['url'], error))
    finally:
        logger.info(' [x] {} {} {} code {} seconds {}'.format(message['uuid'], message['url'], response.request.method, response.status_code, response.elapsed.total_seconds()))
        logger.debug(' [x] {} {} {}'.format(message['uuid'], message['url'], response.text))
        domain_data['lock'] = False
        domain_redis.set(domain, json.dumps(domain_data))
    return response


def make_scan_task(uuid, message):
    """
    Add a task to scan the data
    """
    logger.info(' [x] {} message to scan queue'.format(uuid))
    channel.basic_publish(
        exchange='',
        routing_key='scan_queue',
        body=message,
        properties=pika.BasicProperties(delivery_mode=2))
    logger.info(' [x] {} added message to scan queue complete'.format(uuid))
    uuid_redis.set(uuid, message)
    logger.info(' [x] {} update uuid database complete'.format(uuid))


def callback(ch, method, properties, body):
    logger.info(' [x] message received')
    message = json.loads(body)
    uuid = message['uuid']
    logger.info(' [x] {} message: {}'.format(uuid, message))
    results = {'type': 'error', 'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    try:
        task = [x for x in message['data'] if x['type'] == 'get'][0]
        logger.info(' [x] {} url {} received'.format(uuid, message['url']))
        domain_data = domain_redis.get(task['domain'])
        if domain_data is None:
            domain_data = check_robots(message)
        else:
            domain_data = json.loads(domain_data)
            if domain_data['lock'] is True:
                logger.info(' [x] {} domain {} locked, rejecting'.format(uuid, task['domain']))
                return
        if domain_data['depth'] > MAX_DEPTH:
            raise StopIteration('depth: {} > {}'.format(domain_data['depth'], MAX_DEPTH))
        status = 'started'
        response = pull_data(message, domain_data)
        blob_name = '{}.html'.format(uuid)
        upload_blob(USER_BUCKET, response.text, blob_name)
        time.sleep(domain_data['crawl_delay'])
        results = {
            'type': 'scan',
            'method': response.request.method,
            'code': response.status_code,
            'time': response.elapsed.total_seconds(),
            'local': 'gs://{}/{}'.format(USER_BUCKET, blob_name),
            'depth': domain_data['depth'] + 1
        }
    except StopIteration as err:
        logger.info(' [x] {} depth limited {}'.format(message['uuid'], str(err)))
        status = 'limited'
        results = {'type': 'limited', 'status': str(err)}
    except Exception as err:
        logger.error(' [x] {} failed to read web page {}'.format(message['uuid'], str(err)))
        status = 'failed'
        results = {'type': 'error', 'error': str(err)}
    message['data'].append(results)
    message['status'] = status
    response_pickled = json.dumps(message)
    try:
        make_scan_task(message['uuid'], response_pickled)
    except Exception as err:
        logger.error(' [x] {} failed to make scan task {}'.format(message['uuid'], str(err)))
    else:
        logger.info(' [x] {} web message complete'.format(message['uuid']))
    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info(' [*] consuming messages on task_queue, to exit press CTRL+C')
channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_message_callback=callback, queue='task_queue', consumer_tag=ip_addr)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
connection.close()
