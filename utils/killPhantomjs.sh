#!/bin/bash
# phantomjs has memory leak, this script help to kill
# see https://github.com/ariya/phantomjs/issues/12903
ps -uax| grep phantomjs|sed 's/[^ ]\+ \+\([^ ]\+\) \+.*/kill -9 \1/'| bash
