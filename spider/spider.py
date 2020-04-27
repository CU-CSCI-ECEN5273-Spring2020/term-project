#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
spider.py
gerhard van andel
"""
import sys
import json
import socket
import time
from datetime import datetime
from random import randint
from urllib.robotparser import RobotFileParser

import pika
import requests
import common
from google.cloud import storage

start_datetime = datetime.utcnow()
logger = common.setup_logger(__name__)

if not common.wait_for_connection(logger):
    logger.error(' [*] failed to connect, exiting')
    sys.exit(1)


USER_AGENT = f'asynchronousgillz, 1.1; requests, {requests.__version__};'
USER_DELAY = 10
USER_DEPTH = 1
MAX_DEPTH = 5
MAX_PULL_COUNT = 20
BT_INSTANCE = 'term-project-test-west-1'


def upload_blob(bucket_name, source_data, destination_blob_name):
    """
    Uploads a file to the bucket
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(source_data, content_type='text/html')
    logger.info(' [x] file {} uploaded to {}'.format(destination_blob_name, bucket_name))


def check_robots(identifier, task):
    """
    Pulls the robots.txt if present
    """
    domain_data = common.get_domain_redis().get(task['domain'])
    if domain_data is not None:
        domain_data = json.loads(domain_data)
    else:
        url = '{}://{}/robots.txt'.format(task['scheme'], task['domain'])
        logger.info(' [x] {} RobotFileParser {} '.format(identifier, url))
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
        logger.info(' [x] {} saved domain data {}'.format(identifier, task['domain']))
        logger.debug(' [x] {} domain data {}'.format(identifier, domain_data))
        common.get_domain_redis().set(task['domain'], json.dumps(domain_data), ex=120)
        logger.info(' [x] {} {} validation results {}'.format(identifier, url, valid_url))
        if not valid_url:
            raise ValueError('robot.txt rule validation failed')
    return domain_data


def pull_data(identifier, correlation, task, domain_data):
    """
    Pull the html data
    """
    domain = domain_data['domain']
    domain_data = json.loads(common.get_domain_redis().get(domain))
    if not domain_data or domain_data['lock']:
        raise ResourceWarning(f'{identifier} lock unavailable for domain {domain}, skipping')
    domain_data['lock'] = True
    common.get_domain_redis().set(domain, json.dumps(domain_data), ex=120)
    logger.info(' [x] {} lock acquired for domain {}'.format(identifier, domain_data['domain']))
    response = None
    try:
        logger.info(' [x] {} GET {}'.format(identifier, task['url']))
        response = requests.get(task['url'], headers={'user-agent': USER_AGENT})
        if response.status_code < 500:
            h = common.domain_hash(correlation, task['url'])
            common.get_domain_redis().set(h, identifier)
            logger.info(' [x] {} hash {} {} set'.format(identifier, task['url'], h))
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        logger.error(' [x] {} {} {}'.format(identifier, task['url'], err))
        raise err
    finally:
        logger.info(' [x] {} {} {} {} {}'.format(identifier, task['url'], response.request.method, response.status_code, response.elapsed.total_seconds()))
        logger.debug(' [x] {} {} {}'.format(identifier, task['url'], response.text))
        logger.info(' [x] {} lock sleep {} seconds for domain {}'.format(identifier, domain_data['crawl_delay'], domain_data['domain']))
        time.sleep(domain_data['crawl_delay'])
        domain_data['lock'] = False
        common.get_domain_redis().set(domain, json.dumps(domain_data), ex=120)
        logger.debug(' [x] {} {} {}'.format(identifier, task['url'], response.text))
        logger.info(' [x] {} lock released for domain {}'.format(identifier, domain_data['domain']))
    return response


def make_scan_task(identifier, message):
    """
    Add a task to scan the data
    """
    logger.info(' [x] {} establishing connection to rabbitmq'.format(identifier))
    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    logger.info(' [x] {} message to scan queue'.format(identifier))
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
    logger.info(' [x] {} added message to scan queue complete'.format(identifier))


def update_redis(identifier, message):
    """
    Update redis
    """
    logger.info(' [x] {} message to scan queue'.format(identifier))
    common.get_job_redis().set(identifier, message)
    logger.info(' [x] {} update identifier database complete'.format(identifier))


def callback(ch, method, properties, body):
    logger.info(' [x] message received')
    message = json.loads(body)
    identifier = message['identifier']
    correlation = message['correlation']
    logger.info(' [x] {} message: {}'.format(identifier, message))
    results = {'type': 'error', 'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    valid_scan_task = False
    try:
        task = [x for x in message['data'] if x['type'] == 'spider'][0]
        logger.info(' [x] {} url {} received'.format(identifier, task['url']))
        if task['depth'] > MAX_DEPTH:
            raise StopIteration('depth: {} > {}'.format(task['depth'], MAX_DEPTH))
        domain_data = check_robots(identifier, task)
        status = 'spider-crawled'
        response = pull_data(identifier, correlation, task, domain_data)
        blob_name = 'html/{}.html'.format(identifier)
        upload_blob(common.USER_BUCKET, response.text, blob_name)
        data_message = {
            'method': response.request.method,
            'code': response.status_code,
            'time': response.elapsed.total_seconds(),
            'local': 'gs://{}/{}'.format(common.USER_BUCKET, blob_name),
            'depth': domain_data['depth'] + 1,
            'type': 'scan'
        }
        query_data_key = 'domain.{}.{}'.format(domain_data['domain'], identifier)
        response_data = {
            'duration': response.elapsed.total_seconds(),
            'timestamp': datetime.utcnow().isoformat(),
            'url': task['url']
        }
        common.get_stats_redis().set(query_data_key, json.dumps(response_data))
        results.update(data_message)
        valid_scan_task = True
    except ResourceWarning as err:
        logger.info(f' [x] {err}')
        time.sleep(randint(1, task['depth']) ** 2)
        ch.basic_reject(delivery_tag=method.delivery_tag)
        return
    except StopIteration as err:
        logger.info(' [x] {} depth limited {}'.format(message['identifier'], str(err)))
        status = 'limited'
        results.update({'type': 'limited', 'status': str(err)})
    except Exception as err:
        import traceback
        logger.exception(err)
        logger.error(' [x] {} failed to read web page'.format(message['identifier']))
        status = 'failed'
        results.update({'type': 'error', 'error': traceback.format_exc().splitlines()[-1]})
    message['data'].append(results)
    message['status'] = status
    response_pickled = json.dumps(message)
    try:
        if valid_scan_task:
            make_scan_task(message['identifier'], response_pickled)
        update_redis(message['identifier'], response_pickled)
    except Exception as err:
        logger.error(' [x] {} failed to make scan task {}'.format(message['identifier'], str(err)))
    else:
        logger.info(' [x] {} web message complete'.format(message['identifier']))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    ip_addr = socket.gethostbyname(socket.gethostname())
    logger.info(f' [*] ip address is: {ip_addr}')
    logger.info(f' [*] startup time took, {(datetime.utcnow() - start_datetime).total_seconds()} seconds')

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
