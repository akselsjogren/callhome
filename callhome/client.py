import datetime
import logging as log
import os
import stat
import tempfile

import redis

from . import exceptions


def get_all(redis_host, clear=False):
    try:
        r = redis.Redis(host=redis_host, decode_responses=True)
        hosts = r.hgetall("host_alive")
    except redis.ConnectionError as e:
        log.error("%s", e)
        log.debug("redis exception", exc_info=True)
        raise exceptions.CallHomeError(
            "Cannot connect to redis host %r. Set correct host with --redis-host or "
            "environment CALLHOME_REDIS_HOST",
            redis_host,
        )

    log.debug("HGETALL host_alive: %s", hosts)
    ret = []
    for hostname, last_seen in hosts.items():
        last_seen = int(float(last_seen))
        ip = r.get(f"ip:{hostname}")
        log.debug("GET ip:%s -> %s", hostname, ip)
        log.info(
            "%-15s  last seen: %s, ip: %s",
            hostname,
            datetime.datetime.fromtimestamp(last_seen),
            ip,
        )
        if ip:
            ret.append({"host": hostname, "ip": ip, "last_seen": last_seen})
        else:
            if clear:
                log.info("HDEL host_alive %s", hostname)
                r.hdel("host_alive", hostname)
    return ret


def write_hosts_file(host_list, hosts_file, domain: str = None):
    """Write host/address pairs to /etc/hosts from ansible inventory."""
    delimiters = (
        "# --- callhome managed start ---",
        "# --- callhome managed end ---",
    )
    our_lines = []
    for host in host_list:
        line = "%(ip)s %(host)s" % host
        if domain:
            line += f" {host['host']}.{domain}"
        our_lines.append(line)
    if not our_lines:
        log.warning("Inventory seems empty, not writing anything.")
        return

    with open(hosts_file) as f:
        data = f.read()
    new = []
    in_block = False
    for line in data.splitlines():
        if line == delimiters[0]:
            in_block = True
            new.append(line)
        elif line == delimiters[1]:
            in_block = False
            new += our_lines
            our_lines = []
            new.append(line)
        elif in_block:
            log.debug("old entry: %s", line)
        else:
            new.append(line)
    assert not in_block
    assert len(new)
    if our_lines:
        new.append(delimiters[0])
        new += our_lines
        new.append(delimiters[1])
    new_data = "\n".join(new) + "\n"

    tempfd, tempname = _mktemp()
    log.info("Write new host file to %s", tempname)
    os.chmod(tempfd, stat.S_IRUSR | stat.S_IWUSR | stat.S_IROTH)
    with open(tempfd, "w") as f:
        f.write(new_data)
    return tempname


def _mktemp():
    return tempfile.mkstemp()
