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
import redis
import common
from flask import Flask, request, Response

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
        import traceback
        app.logger.exception(err)
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
    encode response using jsonpickle
    """
    response = common.get_job_redis().get(identifier)
    if response is None:
        status = 404
    else:
        status = 200
        response = json.loads(response)
    json_response = json.dumps(response)
    return Response(response=json_response, status=status, mimetype="application/json")


# route http get to this method
@app.route('/api/stats', methods=['GET'], endpoint='get_stats')
def get_stats():
    """
    build a response dict to send back to client
    encode response using jsonpickle
    """
    status = 200
    response = {'status': 'OK', 'data': list()}
    try:
        r = common.get_stats_redis()
        for req in r.keys():
            key = req.decode()
            logger.debug(f'searching for key {key}')
            point = json.loads(r.get(key))
            response['data'].append(point)
    except Exception as err:
        import traceback
        app.logger.exception(err)
        response = {'type': 'error', 'error': traceback.format_exc().splitlines()[-1]}
        status = 400
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
