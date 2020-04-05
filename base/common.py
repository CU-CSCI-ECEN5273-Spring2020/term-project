#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
"""
common.py
gerhard van andel
"""
import logging
import socket
import time


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
    return is_reachable
