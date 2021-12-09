import argparse
import logging as log
import sys

from .exceptions import CallHomeError
from . import service


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("--redis-host", default="localhost")
    parser.add_argument("--interval", type=int, default=3600)
    parser.add_argument("--systemd", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    log_format = "{}%(levelname)-8s %(message)s".format(
        "%(asctime)s " if not args.systemd else ""
    )
    log.basicConfig(
        level=max(log.WARNING - args.verbose * 10, log.DEBUG), format=log_format
    )

    srv = service.CallHome(args.redis_host)
    srv.run(interval=args.interval)


if __name__ == "__main__":
    try:
        main()
    except CallHomeError as exc:
        log.error("%s", exc)
        sys.exit(exc.retcode)
