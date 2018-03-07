#!/bin/bash

#crawl content of feeds
curl -XGET http://localhost:12345/api/schedule/contents_crawl

#predict topics on already crawled content
curl -XGET http://localhost:12345/api/schedule/contents_predict

#generate machine learning topics prediction models
curl -XGET http://localhost:12345/api/schedule/generate_model
