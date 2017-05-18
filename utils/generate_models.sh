#!/bin/bash
pid=`cat /var/run/dfm_generate_models.pid`
echo "Current PID:$pid"
if [[ -z "$pid" || ! ( -e /proc/$pid && -a /proc/$pid/exe ) ]]; then
  ((curl -XGET "http://localhost:12345/api/schedule/generate_models") & echo $! > /var/run/dfm_generate_models.pid &)
  pid=`cat /var/run/dfm_generate_models.pid`
  echo "new process is $pid"
fi
