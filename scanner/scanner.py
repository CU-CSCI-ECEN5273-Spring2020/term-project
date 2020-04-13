#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
scanner.py
gerhard van andel
"""
import json
import socket
import sys
import uuid
from datetime import datetime

import pika
import redis
import common
from bs4 import BeautifulSoup
from google.cloud import storage

TASK_LINK_LIMIT = 5

start_datetime = datetime.utcnow()
logger = common.setup_logger(__name__)

if not common.wait_for_connection(logger):
    logger.error(' [*] failed to connect, exiting')
    sys.exit(1)


def download_blob(bucket_name, blob_name):
    """Downloads a blob from the bucket."""
    logger.info(' [x] pulling data from bucket {} blob {}'.format(bucket_name, blob_name))
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    source_data = blob.download_as_string()
    logger.info(' [x] bucket {} blob {} downloaded len: {}'.format(bucket_name, blob_name, len(source_data)))
    return source_data


def parse_web_page(identifier, correlation, task):
    """ lets get the links in the web page"""
    logger.info(' [x] {} BeautifulSoup start'.format(identifier))
    gs_local = task['local'].split('/')
    bucket_name, blob = gs_local[-2:]
    logger.info(' [x] {} bucket_name: {} blob: {}'.format(identifier, bucket_name, blob))
    content = download_blob(bucket_name, blob)
    logger.info(' [x] {} content received'.format(identifier))
    soup = BeautifulSoup(content, 'html.parser')
    logger.info(' [x] {} BeautifulSoup soup received'.format(identifier))
    page = {'title': soup.title.string, 'links': list()}
    logger.info(' [x] {} url {} received'.format(identifier, soup.title.string))
    task_link_count = 0
    for link in soup.find_all('a'):
        try:
            task = common.make_spider_task(link['href'], task['depth'])
            h = common.domain_hash(correlation, task['url'])
            if common.get_domain_redis().get(h):
                logger.info(' [x] {} {} has already seen url {} skipping'.format(identifier, correlation, task['url']))
                continue
            task['identifier'] = str(uuid.uuid4())
            logger.info(' [x] {} task made for url: {}'.format(identifier, link['href']))
            page['links'].append(task)
        except (ValueError, KeyError):
            logger.debug(' [x] {} skipping {}'.format(identifier, link))
        except StopIteration:
            logger.debug(' [x] {} skipping {}'.format(identifier, link))
        # To test depth not amount of links
        task_link_count += 1
        if task_link_count > TASK_LINK_LIMIT:
            break
    logger.info(' [x] {} BeautifulSoup complete'.format(identifier))
    return page


def add_tasks(correlation, task_list):
    """
    """
    # Initialize the rabbitmq connection
    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='task_queue', durable=True)
    for task in task_list:
        logger.info(' [x] add task: {}'.format(task))
        identifier = task['identifier']
        logger.info(' [x] task identifier generated: {} correlation {}'.format(identifier, correlation))
        ret = {
            'status': 'queued',
            'identifier': identifier,
            'correlation': correlation,
            'data': [task]
        }
        logger.info('* task generated: {}'.format(ret))
        message = json.dumps(ret)
        channel.basic_publish(
            exchange='',
            routing_key='spider_queue',
            properties=pika.BasicProperties(
                content_type='application/json',
                content_encoding='UTF-8',
                delivery_mode=2
            ),
            body=message,
        )
        # Initialize the Redis connection
        uuid_redis = redis.StrictRedis(host='redis', port=6379, db=1)
        uuid_redis.set(identifier, message)
    # Close the RabbitMQ connection
    connection.close()
    logger.info(' [x] {} complete'.format(correlation))


def callback(ch, method, properties, body):
    logger.info(' [x] message received')
    message = json.loads(body)
    identifier = message['identifier']
    correlation = message['correlation'] if message['correlation'] else identifier
    logger.info(' [x] {} message: {}'.format(identifier, message))
    results = {'type': 'error', 'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    try:
        task = [x for x in message['data'] if x['type'] == 'scan'][0]
        logger.info(' [x] {} url depth {} received'.format(identifier, task['depth']))
        parsed_data = parse_web_page(identifier, correlation, task)
        logger.info(' [x] {} web information parsed now making tasks'.format(identifier))
        add_tasks(correlation, parsed_data['links'])
        results.update({'type': 'scan', 'data': parsed_data})
        status = 'scan-complete'
    except Exception as err:
        import traceback
        logger.exception(err)
        logger.error(' [x] {} failed'.format(identifier))
        results = {'type': 'error', 'error': traceback.format_exc().splitlines()[-1]}
        status = 'failed'
    results['timestamp'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    message['data'].append(results)
    message['status'] = status
    response_pickled = json.dumps(message)
    # Initialize the Redis connection
    uuid_redis = redis.StrictRedis(host='redis', port=6379, db=1)
    uuid_redis.set(message['identifier'], response_pickled)
    logger.info(' [x] {} message complete'.format(message['identifier']))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    ip_addr = socket.gethostbyname(socket.gethostname())
    logger.info(' [*] ip address is: {}'.format(ip_addr))
    logger.info(f' [*] startup time took, {(datetime.utcnow() - start_datetime).total_seconds()} seconds')

    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()

    channel.queue_declare(queue='scan_queue', durable=True)

    logger.info(' [*] waiting for messages. To exit press CTRL+C')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(on_message_callback=callback, queue='scan_queue', consumer_tag=ip_addr)

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
