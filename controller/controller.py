#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
controller.py
gerhard van andel
"""
import sys
import json
import uuid
import socket
from datetime import datetime

import pika
import common
from flask import Flask, request, Response
from google.cloud import storage
from google.cloud.exceptions import NotFound

start_datetime = datetime.utcnow()
logger = common.setup_logger(__name__)

if not common.wait_for_connection(logger):
    logger.error(' [*] failed to connect, exiting')
    sys.exit(1)

ip_addr = socket.gethostbyname(socket.gethostname())
logger.info(' [*] ip address is: {}'.format(ip_addr))
logger.info(f' [*] startup time took, {(datetime.utcnow() - start_datetime).total_seconds()} seconds')

# Initialize the Flask application
app = Flask(__name__)
app.logger = logger


# route http get to this method
@app.route('/api/status', methods=['GET'], endpoint='get_status')
def get_status():
    """
    Get the status of the system
    """
    status = 200
    response = {
        'redis': common.get_stats_redis().info()
    }
    json_response = json.dumps(response)
    return Response(response=json_response, status=status, mimetype="application/json")


def download_blob(bucket_name, blob_name):
    """Downloads a blob from the bucket."""
    logger.info(' [x] pulling data from bucket {} blob {}'.format(bucket_name, blob_name))
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    source_data = blob.download_as_string()
    logger.info(' [x] bucket {} blob {} downloaded len: {}'.format(bucket_name, blob_name, len(source_data)))
    return source_data


# route http posts to this method
@app.route('/api/url', methods=['POST'], endpoint='url')
def url():
    """
    send a url to be scanned
    """
    content = request.json
    status = 200
    request_url = None
    try:
        request_url = content['url']
        task = common.make_spider_task(request_url)
        app.logger.info('* task made for url: {}'.format(request_url))
        response = add_spider_task(task)
        app.logger.info('* task added: {}'.format(task))
    except Exception as err:
        app.logger.exception(err)
        import traceback
        response = {'type': 'error', 'error': traceback.format_exc().splitlines()[-1], 'url': request_url}
        status = 400
    json_response = json.dumps(response)
    return Response(response=json_response, status=status, mimetype="application/json")


def add_spider_task(task):
    """
    """
    # Initialize the rabbitmq connection
    app.logger.info('* add task: {}'.format(task))
    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='task_queue', durable=True)
    identifier = str(uuid.uuid4())
    app.logger.info('* task identifier generated: {}'.format(identifier))
    ret = {
        'status': 'queued',
        'identifier': identifier,
        'correlation': identifier,
        'data': [task]
    }
    app.logger.info('* task generated: {}'.format(ret))
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
    connection.close()
    # Initialize the Redis connection
    common.get_job_redis().set(identifier, message)
    return ret


# route http get to this method
@app.route('/api/url/<identifier>', methods=['GET'], endpoint='get_url')
def get_url(identifier):
    """
    build a response dict to send back to client
    encode response using json
    """
    try:
        response = common.get_job_redis().get(identifier)
        if response is not None:
            status = 200
            response = json.loads(response)
        else:
            response = download_blob(common.USER_BUCKET, f'data/{identifier}.json')
            status = 200
            response = json.loads(response)
    except NotFound as err:
        app.logger.exception(err)
        response = {'type': 'error', 'error': 'not found', 'identifier': identifier}
        status = 404
    except Exception as err:
        app.logger.exception(err)
        import traceback
        response = {'type': 'error', 'error': traceback.format_exc().splitlines()[-1], 'identifier': identifier}
        status = 400
    json_response = json.dumps(response)
    return Response(response=json_response, status=status, mimetype="application/json")


# route http get to this method
@app.route('/api/stats', methods=['GET'], endpoint='get_stats')
def get_stats():
    """
    build a response list to send back to client with times of page loads
    encode response using json
    """
    status = 200
    response = {'status': 'OK', 'data': list(), 'total': 0}
    try:
        r = common.get_stats_redis()
        for req in r.keys():
            key = req.decode()
            logger.debug(f'searching for key {key}')
            point = json.loads(r.get(key))
            response['data'].append(point)
            response['total'] += 1
    except Exception as err:
        import traceback
        app.logger.exception(err)
        response = {'type': 'error', 'error': traceback.format_exc().splitlines()[-1]}
        status = 400
    json_response = json.dumps(response)
    return Response(response=json_response, status=status, mimetype='application/json')


# route http get to this method
@app.route('/api/queues', methods=['GET'], endpoint='get_queues')
def get_queues():
    """
    build a response list of current queues
    encode response using json
    """
    status = 200
    response = {'status': 'OK', 'queues': list(), 'total': 0}
    app.logger.info('* get queues')
    try:
        credentials = pika.PlainCredentials('guest', 'guest')
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
        channel = connection.channel()
        for queue_name in ('spider_queue', 'scan_queue', 'cleanup_queue'):
            queue = channel.queue_declare(queue=queue_name, durable=True)
            queue_count = queue.method.message_count
            response['total'] += queue_count
            response['queues'].append({'queue': queue_name, 'count': queue_count})
        connection.close()
    except Exception as err:
        app.logger.exception(err)
        import traceback
        response = {'type': 'error', 'error': traceback.format_exc().splitlines()[-1]}
        status = 400
    json_response = json.dumps(response)
    return Response(response=json_response, status=status, mimetype='application/json')


# start flask app
if __name__ == '__main__':
    try:
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(error, file=sys.stderr)
        import traceback
        traceback.print_exc()
