import logging as log
import os
import signal
import socket
import threading
import time

import redis

from .exceptions import CallHomeError


class Agent:
    def __init__(self, redis_host):
        self._redis_host = redis_host
        self._ip = None
        self._hostname = socket.gethostname()
        log.debug("gethostname() -> %s", self._hostname)

    def run(
        self,
        *,
        interval=3600,
        expire_seconds=7200,
        max_conn_attemps=100,
        remove_on_exit=False
    ):
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
        if remove_on_exit:
            self._deregister()
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

    def _deregister(self):
        r = redis.Redis(host=self._redis_host, decode_responses=True)
        log.info("De-register '%s'", self._hostname)
        key = "ip:%s" % self._hostname
        log.debug("redis DEL %r", key)
        r.delete(key)

    @staticmethod
    def _get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("198.51.100.254", 1))  # Arbitrary address via default route
            ipaddr = s.getsockname()[0]
        except Exception:
            ipaddr = "127.0.0.1"
        finally:
            s.close()
        return ipaddr
