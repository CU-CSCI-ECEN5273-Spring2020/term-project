#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
spider.py
gerhard van andel
"""
import sys
import base64
import json
import socket
import time
import hashlib
from datetime import datetime
from random import randint
from urllib.robotparser import RobotFileParser

import pika
import redis
import requests
from common import setup_logger, wait_for_connection
from google.cloud import storage

logger = setup_logger(__name__)

if not wait_for_connection(logger):
    logger.error(' [*] failed to connect, exiting')
    sys.exit(1)

USER_AGENT = 'asynchronousgillz, 1.1; requests, {}'.format(requests.__version__)
USER_DELAY = 10
USER_DEPTH = 1
USER_BUCKET = 'term-project'
MAX_DEPTH = 5
MAX_PULL_COUNT = 20


def string_to_base64(s):
    return base64.b64encode(s.encode('utf-8'))


def base64_to_string(b):
    return base64.b64decode(b).decode('utf-8')


def get_domain_redis():
    return redis.StrictRedis(host='redis', port=6379, db=2)


def get_uuid_redis():
    return redis.StrictRedis(host='redis', port=6379, db=1)


def upload_blob(bucket_name, source_data, destination_blob_name):
    """
    Uploads a file to the bucket
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(source_data, content_type='text/html')
    logger.info(' [x] file {} uploaded to {}'.format(destination_blob_name, bucket_name))


def check_robots(uuid, task):
    """
    Pulls the robots.txt if present
    """
    domain_data = get_domain_redis().get(task['domain'])
    if domain_data is not None:
        domain_data = json.loads(domain_data)
    else:
        url = '{}://{}/robots.txt'.format(task['scheme'], task['domain'])
        logger.info(' [x] {} RobotFileParser {} '.format(uuid, url))
        rp = RobotFileParser(url=url)
        rp.read()
        valid_url = rp.can_fetch('*', task['domain'])
        delay = rp.crawl_delay('*')
        domain_data = {
            'domain': task['domain'],
            'valid_url': valid_url,
            'lock': False,
            'crawl_delay': USER_DELAY if delay is None else delay,
            'depth': USER_DEPTH
        }
        logger.info(' [x] {} saved domain data {}'.format(uuid, task['domain']))
        logger.debug(' [x] {} domain data {}'.format(uuid, domain_data))
        get_domain_redis().set(task['domain'], json.dumps(domain_data))
        logger.info(' [x] {} {} validation results {}'.format(uuid, url, valid_url))
        if not valid_url:
            raise ValueError('robot.txt rule validation failed')
    return domain_data


def pull_data(uuid, task, domain_data):
    """
    Pull the html data
    """
    h = hashlib.sha256('{}:{}'.format(uuid, task['url']).encode('utf-8')).hexdigest()
    if get_domain_redis().get(h):
        raise StopIteration(' [x] {} has already seen url {} '.format(uuid, task['url']))
    domain = domain_data['domain']
    domain_lock_try_count = 1
    for domain_lock_try_count in range(1, MAX_PULL_COUNT):
        domain_data = json.loads(get_domain_redis().get(domain))
        if domain_data['lock']:
            sleep_time = (domain_lock_try_count ** 2) + randint(1, 5)
            logger.info(' [x] {} lock unavailable for domain {} retry in {} seconds'.format(uuid, domain, sleep_time))
            time.sleep(sleep_time)
        else:
            break
    if domain_lock_try_count >= MAX_PULL_COUNT - 1:
        raise StopIteration(' [x] {} failed to obtain lock for domain {}'.format(uuid, domain_data['domain']))
    domain_data['lock'] = True
    get_domain_redis().set(domain, json.dumps(domain_data))
    logger.info(' [x] {} lock acquired for domain {}'.format(uuid, domain_data['domain']))
    response = None
    try:
        logger.info(' [x] {} GET {}'.format(uuid, task['url']))
        response = requests.get(task['url'], headers={'user-agent': USER_AGENT})
        response.raise_for_status()
    except requests.exceptions.HTTPError() as err:
        logger.error(' [x] {} {} {}'.format(uuid, task['url'], err))
    finally:
        logger.info(' [x] {} {} {} {} {}'.format(uuid, task['url'], response.request.method, response.status_code, response.elapsed.total_seconds()))
        logger.debug(' [x] {} {} {}'.format(uuid, task['url'], response.text))
        logger.info(' [x] {} lock sleep {} seconds for domain {}'.format(uuid, domain_data['crawl_delay'], domain_data['domain']))
        time.sleep(domain_data['crawl_delay'])
        domain_data['lock'] = False
        get_domain_redis().set(domain, json.dumps(domain_data))
        logger.info(' [x] {} lock released for domain {}'.format(uuid, domain_data['domain']))
    return response


def make_scan_task(uuid, message):
    """
    Add a task to scan the data
    """
    logger.info(' [x] {} establishing connection to rabbitmq'.format(uuid))
    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    logger.info(' [x] {} message to scan queue'.format(uuid))
    channel.basic_publish(
        exchange='',
        routing_key='scan_queue',
        properties=pika.BasicProperties(
            content_type='application/json',
            content_encoding='UTF-8',
            delivery_mode=2
        ),
        body=message,
    )
    connection.close()
    logger.info(' [x] {} added message to scan queue complete'.format(uuid))


def update_redis(uuid, message):
    """
    Update redis
    """
    logger.info(' [x] {} message to scan queue'.format(uuid))
    get_uuid_redis().set(uuid, message)
    logger.info(' [x] {} update uuid database complete'.format(uuid))


def callback(ch, method, properties, body):
    logger.info(' [x] message received')
    message = json.loads(body)
    uuid = message['uuid']
    logger.info(' [x] {} message: {}'.format(uuid, message))
    results = {'type': 'error', 'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    valid_scan_task = False
    try:
        task = [x for x in message['data'] if x['type'] == 'spider'][0]
        logger.info(' [x] {} url {} received'.format(uuid, task['url']))
        if task['depth'] > MAX_DEPTH:
            raise StopIteration('depth: {} > {}'.format(task['depth'], MAX_DEPTH))
        domain_data = check_robots(uuid, task)
        status = 'spider-crawled'
        response = pull_data(uuid, task, domain_data)
        blob_name = '{}.html'.format(uuid)
        upload_blob(USER_BUCKET, response.text, blob_name)
        results.update({
            'type': 'scan',
            'method': response.request.method,
            'code': response.status_code,
            'time': response.elapsed.total_seconds(),
            'local': 'gs://{}/{}'.format(USER_BUCKET, blob_name),
            'depth': domain_data['depth'] + 1
        })
        valid_scan_task = True
    except StopIteration as err:
        logger.info(' [x] {} depth limited {}'.format(message['uuid'], str(err)))
        status = 'limited'
        results.update({'type': 'limited', 'status': str(err)})
    except Exception as err:
        import traceback
        logger.exception(err)
        logger.error(' [x] {} failed to read web page'.format(message['uuid']))
        status = 'failed'
        results.update({'type': 'error', 'error': traceback.format_exc().splitlines()[-1]})
    message['data'].append(results)
    message['status'] = status
    response_pickled = json.dumps(message)
    try:
        if valid_scan_task:
            make_scan_task(message['uuid'], response_pickled)
        update_redis(message['uuid'], response_pickled)
    except Exception as err:
        logger.error(' [x] {} failed to make scan task {}'.format(message['uuid'], str(err)))
    else:
        logger.info(' [x] {} web message complete'.format(message['uuid']))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    ip_addr = socket.gethostbyname(socket.gethostname())
    logger.info(' [*] ip address is: {}'.format(ip_addr))
    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='spider_queue', durable=True)

    logger.info(' [*] waiting for messages. To exit press CTRL+C')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(on_message_callback=callback, queue='spider_queue', consumer_tag=ip_addr)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    connection.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        import traceback
        traceback.print_exc()
