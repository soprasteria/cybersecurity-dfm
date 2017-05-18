#!/bin/bash
pid=`cat /var/run/dfm_contents_crawl.pid`
echo "Current PID:$pid"
if [[ -z "$pid" || ! ( -e /proc/$pid && -a /proc/$pid/exe ) ]]; then
  echo "process doesn't exist aymore, create a new one"
  ((curl -XGET "http://localhost:12345/api/schedule/contents_crawl") & echo $! > /var/run/dfm_contents_crawl.pid &)
  pid=`cat /var/run/dfm_contents_crawl.pid`
  echo "new process is $pid"
fi
