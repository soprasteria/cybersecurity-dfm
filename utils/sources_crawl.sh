#!/bin/bash
pid=`cat /var/run/dfm_sources_crawl.pid`
echo "Current PID:$pid"
if [[ -z "$pid" || ! ( -e /proc/$pid && -a /proc/$pid/exe ) ]]; then
  ((curl -XGET "http://localhost:12345/api/schedule/sources_crawl") & echo $! > /var/run/dfm_sources_crawl.pid &)
  pid=`cat /var/run/dfm_sources_crawl.pid`
  echo "new process is $pid"
fi
