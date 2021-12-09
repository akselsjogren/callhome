import logging as log
import os
import signal
import socket
import threading
import time

import redis

from .exceptions import CallHomeError


class CallHome:
    def __init__(self, redis_host):
        self._redis_host = redis_host
        self._ip = None
        self._hostname = socket.gethostname()
        log.debug("gethostname() -> %s", self._hostname)

    def run(self, *, interval=3600, expire_seconds=7200, max_conn_attemps=100):
        log.info("Starting %s. pid: %d", self.__class__.__name__, os.getpid())
        exit_event = threading.Event()

        def _handler(signum, _):
            log.info("Got signal %d, time to call it quits!", signum)
            exit_event.set()

        signal.signal(signal.SIGTERM, _handler)
        signal.signal(signal.SIGINT, _handler)
        failed_attemps = 0

        while not exit_event.is_set():
            try:
                self._register(self._get_ip(), expire_seconds)
            except redis.RedisError as e:
                failed_attemps += 1
                log.warn("Failed to connect to redis: %s %s", e.__class__.__name__, e)
                log.debug("%s", e.__class__, exc_info=True)
                if failed_attemps >= max_conn_attemps:
                    break
                exit_event.wait(60)
            else:
                failed_attemps = 0
                exit_event.wait(interval)
        if failed_attemps:
            raise CallHomeError(
                "Failed to connect to %s. Attemps: %d", self._redis_host, failed_attemps
            )

    def _register(self, ip, expire_seconds):
        r = redis.Redis(host=self._redis_host, decode_responses=True)
        log.info("Register '%s' with IP address: %s", self._hostname, ip)
        r.hmset("host_alive", {self._hostname: time.time()})
        key = "ip:%s" % self._hostname
        log.debug("redis SET %r %r EX %d", key, ip, expire_seconds)
        r.set(key, ip, ex=expire_seconds)

    def _get_ip(self):
        _, _, ipaddrlist = socket.gethostbyname_ex(self._hostname)
        log.debug("Local addresses: %s", ipaddrlist)
        ip = ipaddrlist[-1]
        return ip
