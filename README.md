# callhome service

[![tests](https://github.com/sjoegren/callhome/actions/workflows/tests.yml/badge.svg)](https://github.com/sjoegren/callhome/actions/workflows/tests.yml)

systemd service that reports systems hostname and IP address to a redis host.

## Build

```
poetry build
```

## Install

```
python3 -m pip install -I --no-deps \
    --prefix=/usr/local \
    --install-option="--install-scripts=/usr/local/libexec" \
    callhome-VERSION.tar.gz
```

### Configure systemd service

```
echo "REDIS_HOST=my-redis-server.example.com" > /etc/sysconfig/callhome
```

Install [callhome.service](callhome.service)

```
cp callhome.service /etc/systemd/system/callhome.service
systemctl daemon-reload
systemctl enable --now callhome
```

## Redis

```
# docker run --rm -it redis redis-cli -h redis-host.example.com
172.16.41.200:6379> HGETALL host_alive
1) "foobar"
2) "1639068570.3403447"
172.16.41.200:6379> GET ip:foobar
"192.0.2.100"
```
