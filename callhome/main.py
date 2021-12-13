import argparse
import json
import logging as log
import os
import subprocess
import sys

from .exceptions import CallHomeError
from . import client
from . import service


def _agent():
    parser = _argp()
    parser.add_argument("--interval", type=int, default=3600)
    parser.add_argument(
        "--remove-on-exit",
        action="store_true",
        help="Remove ip address entry on SIGTERM",
    )
    args = parser.parse_args()
    _init_logging(args)

    srv = service.Agent(args.redis_host)
    srv.run(interval=args.interval, remove_on_exit=args.remove_on_exit)


def _client():
    parser = _argp()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--hosts-domain", default=os.environ.get("CALLHOME_DOMAIN"))
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete hosts without stored IPs from redis db",
    )
    args = parser.parse_args()
    _init_logging(args)
    hosts = client.get_all(args.redis_host, args.clear)
    if args.json:
        print(json.dumps(hosts))
    else:
        for host in hosts:
            print("%(host)s\t%(ip)s" % host)

    hosts_path = "/etc/hosts"
    tempfile = client.write_hosts_file(hosts, hosts_path, args.hosts_domain)
    print("Wrote hosts to %s" % tempfile)
    if input(f"copy {tempfile} to {hosts_path}? [y/N]: ") in ("y", "Y"):
        subprocess.run(
            ["sudo", "install", "-v", "-b", "--mode=644", tempfile, hosts_path],
            check=True,
        )
    os.unlink(tempfile)


def _init_logging(args):
    log.basicConfig(
        level=max(log.WARNING - args.verbose * 10, log.DEBUG),
        format="%(levelname)-8s %(message)s",
    )


def _argp():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument(
        "--redis-host", default=os.environ.get("CALLHOME_REDIS_HOST", "localhost")
    )
    return parser


def cli_agent():
    try:
        _agent()
    except CallHomeError as exc:
        log.error("%s", exc)
        sys.exit(exc.retcode)


def cli_client():
    try:
        _client()
    except CallHomeError as exc:
        log.error("%s", exc)
        sys.exit(exc.retcode)
