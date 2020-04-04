#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
scanner.py
gerhard van andel
"""
import base64
import json
import logging
import socket
import sys
import time
from datetime import datetime

import pika
import redis
from bs4 import BeautifulSoup
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


ping_counter = 1
is_reachable = False
while is_reachable is False and ping_counter < 10:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('rabbitmq', 5672))
        is_reachable = True
    except socket.error as e:
        logger.error(f' [*] failed to connect, retry in {ping_counter ** 2} seconds')
        time.sleep(ping_counter ** 2)
        ping_counter += 1
    sock.close()

if not is_reachable:
    logger.info(' [*] failed to connect, exiting')
    sys.exit(1)

# Initialize the rabbitmq connection
credentials = pika.PlainCredentials('guest', 'guest')
connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
channel = connection.channel()

channel.queue_declare(queue='scan_queue', durable=True)

ip_addr = socket.gethostbyname(socket.gethostname())
logger.info(' [*] ip address is: {}'.format(ip_addr))


def string_to_base64(s):
    return base64.b64encode(s.encode('utf-8'))


def base64_to_string(b):
    return base64.b64decode(b).decode('utf-8')


def download_blob(bucket_name, blob_name):
    """Downloads a blob from the bucket."""
    logger.info(' [x] pulling data from bucket {} blob {}'.format(bucket_name, blob_name))
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    source_data = blob.download_as_string()
    logger.info(' [x] bucket {} blob {} downloaded len: {}'.format(bucket_name, blob_name, len(source_data)))
    return source_data


def parse_web_page(uuid, task):
    """ lets get the links in the web page"""
    logger.info(' [x] {} BeautifulSoup start'.format(uuid))
    gs_local = task['local'].split('/')
    bucket_name, blob = gs_local[-2:]
    logger.info(' [x] {} bucket_name: {} blob: {}'.format(uuid, bucket_name, blob))
    content = download_blob(bucket_name, blob)
    logger.info(' [x] {} content received'.format(uuid))
    soup = BeautifulSoup(content, 'html.parser')
    logger.info(' [x] {} BeautifulSoup soup received'.format(uuid))
    page = {'title': soup.title.string, 'data': []}
    logger.info(' [x] {} url {} received'.format(uuid, soup.title.string))
    link_data = []
    for link in soup.find_all('a'):
        href = link['href'] 
        text = link.getText()
        link_data.append({'href': href, 'text': text})
    logger.info(' [x] {} BeautifulSoup soup link count: {}'.format(uuid, len(link_data)))
    page['data'].append({'type': 'links', 'data': link_data})
    text_data = []
    index_count = 0
    for paragraph in soup.find_all('p'):
        text_data.append(paragraph.text)
        index_count += 1
        if index_count > 10:
            break
    logger.info(' [x] {} BeautifulSoup soup paragraphs count: {}'.format(uuid, len(text_data)))
    page['data'].append({'type': 'text', 'data': text_data})
    logger.info(' [x] {} BeautifulSoup complete'.format(uuid))
    return page


def callback(ch, method, properties, body):
    logger.info(' [x] message received')
    message = json.loads(body)
    uuid = message['uuid']
    logger.info(' [x] {} message: {}'.format(uuid, message))
    results = {'type': 'error', 'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    try:
        task = [x for x in message['data'] if x['type'] == 'scan'][0]
        logger.info(' [x] {} url depth {} received'.format(uuid, task['depth']))
        parsed_data = parse_web_page(uuid, task)
        results.update({'type': 'scan', 'data': parsed_data})
        status = 'scan-complete'
    except Exception as err:
        logger.exception(err)
        logger.error(' [x] {} failed'.format(uuid))
        results = {'type': 'error', 'error': str(err)}
        status = 'failed'
    results['timestamp'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    message['data'].append(results)
    message['status'] = status
    response_pickled = json.dumps(message)
    # Initialize the Redis connection
    uuid_redis = redis.StrictRedis(host='redis', port=6379, db=1)
    uuid_redis.set(message['uuid'], response_pickled)
    logger.info(' [x] {} message complete'.format(message['uuid']))
    ch.basic_ack(delivery_tag=method.delivery_tag)


logger.info(' [*] waiting for messages. To exit press CTRL+C')
channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_message_callback=callback, queue='scan_queue', consumer_tag=ip_addr)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
connection.close()
