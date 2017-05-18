#!/bin/bash
# require in elasticsearch.yml
# script.inline: on
# script.indexed: on
# https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-update-by-query.html
curl -XPOST 'localhost:9200/watch/doc/_update_by_query' -d '{
    "script": {
      "inline": "ctx._source.remove(\"topics\")"
    },
    "query":{ "type" : {"value" : "doc"} }
}'
