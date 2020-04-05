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
from urllib.parse import urlparse
from datetime import datetime

import pika
import redis
from common import setup_logger, wait_for_connection
from flask import Flask, request, Response

logger = setup_logger(__name__)

if not wait_for_connection(logger):
    logger.error(' [*] failed to connect, exiting')
    sys.exit(1)

ip_addr = socket.gethostbyname(socket.gethostname())
logger.info(' [*] ip address is: {}'.format(ip_addr))

# Initialize the Flask application
app = Flask(__name__)
app.logger = logger


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
        task = make_task(request_url)
        app.logger.info('* task made for url: {}'.format(request_url))
        response = add_task(task)
        app.logger.info('* task added: {}'.format(task))
    except Exception as err:
        import traceback
        app.logger.exception(err)
        response = {'type': 'error', 'error': traceback.format_exc().splitlines()[-1], 'url': request_url}
        status = 400
    json_response = json.dumps(response)
    return Response(response=json_response, status=status, mimetype="application/json")


def make_task(input_url):
    """
    """
    url_data = urlparse(input_url)
    if url_data.netloc == '' or url_data.scheme == '':
        raise ValueError('invalid url {}'.format(input_url))
    return {
        'type': 'spider',
        'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        'domain': url_data.netloc,
        'scheme': url_data.scheme,
        'path': url_data.path,
        'depth': 1,
        'url': url_data.geturl()
    }


def add_task(task):
    """
    """
    # Initialize the rabbitmq connection
    app.logger.info('* add task: {}'.format(task))
    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='task_queue', durable=True)
    identifier = str(uuid.uuid4())
    app.logger.info('* task uuid generated: {}'.format(identifier))
    ret = {
        'status': 'queued',
        'uuid': identifier,
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
    uuid_redis = redis.StrictRedis(host='redis', port=6379, db=1)
    uuid_redis.set(identifier, message)
    return ret


# route http get to this method
@app.route('/api/url/<identifier>', methods=['GET'], endpoint='get_url')
def get_url(identifier):
    """
    build a response dict to send back to client
    encode response using jsonpickle
    """
    uuid_redis = redis.StrictRedis(host='redis', port=6379, db=1)
    response = uuid_redis.get(identifier)
    if response is None:
        status = 404
    else:
        status = 200
        response = json.loads(response)
    json_response = json.dumps(response)
    return Response(response=json_response, status=status, mimetype="application/json")


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
