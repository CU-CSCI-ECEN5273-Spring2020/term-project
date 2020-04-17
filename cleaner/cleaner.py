#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
cleaner.py
gerhard van andel
"""
import json
import socket
import sys
from datetime import datetime

import pika
import common
from google.cloud import storage


start_datetime = datetime.utcnow()
logger = common.setup_logger(__name__)

if not common.wait_for_connection(logger):
    logger.error(' [*] failed to connect, exiting')
    sys.exit(1)


def upload_blob(bucket_name, source_data, destination_blob_name):
    """
    Uploads a file to the bucket
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(source_data, content_type='application/json')
    logger.info(' [x] file {} uploaded to {}'.format(destination_blob_name, bucket_name))


def callback(ch, method, properties, body):
    logger.info(' [x] message received')
    message = json.loads(body)
    identifier = message['identifier']
    logger.info(f' [x] {identifier} message: {message}')
    try:
        logger.info(f' [x] {identifier} cleanup request received')
        message['status'] = 'cleanup-complete'
        response_pickled = json.dumps(message)
        blob_name = f'data/{identifier}.json'
        upload_blob(common.USER_BUCKET, response_pickled, blob_name)
        common.get_job_redis().delete(identifier)
    except Exception as err:
        import traceback
        logger.exception(err)
        logger.error(f' [x] {identifier} failed')
    logger.info(' [x] {} message complete'.format(message['identifier']))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    ip_addr = socket.gethostbyname(socket.gethostname())
    logger.info(' [*] ip address is: {}'.format(ip_addr))
    logger.info(f' [*] startup time took, {(datetime.utcnow() - start_datetime).total_seconds()} seconds')

    credentials = pika.PlainCredentials('guest', 'guest')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()

    channel.queue_declare(queue='cleanup_queue', durable=True)

    logger.info(' [*] waiting for messages. To exit press CTRL+C')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(on_message_callback=callback, queue='cleanup_queue', consumer_tag=ip_addr)

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
