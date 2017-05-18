#!/bin/bash
pid=`cat /var/run/dfm_contents_predict.pid`
echo "Current PID:$pid"
if [[ -z "$pid" || ! ( -e /proc/$pid && -a /proc/$pid/exe ) ]]; then
  ((curl -XGET "http://localhost:12345/api/schedule/contents_predict") & echo $! > /var/run/dfm_contents_predict.pid &)
  pid=`cat /var/run/dfm_contents_predict.pid`
  echo "new process is $pid"
fi
