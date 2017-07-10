#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"Data Feed Manager Web Server for REST API"

""" Import utilities """

import io
import os
import types
import errno
import shutil
import inspect
import resource
from memory_profiler import profile
from subprocess import call
import multiprocessing
import time
import datetime
import iso8601
import gc
import urllib2
from urlparse import urljoin
import unicodecsv as csv
import json
from langdetect import detect
from modeltrainer import ModelTrainer

from multiprocessing import Lock, Process, Queue, current_process
""" Use multiprocessing with Workers defined in settings for concurrent crawl on web page content"""

#from dd_client import DD, DDCommunicationError
from dd_client import DD
""" Deep Detect client library import """

#"""Virtual screen to run real web browsers"""
#from pyvirtualdisplay import Display

from flask import Flask, request, send_from_directory, redirect, render_template, Response
""" Use Flask to deliver web page, doc, and rest api """
#from flask.ext.autodoc import Autodoc
from flask_restful import Resource, Api, reqparse
""" Use flask_restful module for rest api """

""" Use of logging API to define logging level, most of messages are at DEBUG level"""


from werkzeug.contrib.atom import AtomFeed
""" using Werkzeug to generate rss feed (atom) """

import logging
""" Use python standard logging module """
from logging.handlers import RotatingFileHandler

from storage import Storage
""" Use submodule storage for ElasticSearch"""
from results import Results
""" Results object class """
from feed import Feed
""" Use submodule feed to crawl and parse sources news and contents """

def limit_memory(maxsize):
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (maxsize, hard))


def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True

def generate_uuid(data):
     """ Generate UUID for any entry in ElasticSearch

     :param: dict data Item's data to insert in ES
     :result: item_id
     """
     #mandatory to instantiate md5 just before update otherwise different hash is generated
     hasher=hashlib.md5()
     full_uri=data['link'].encode('utf-8','xmlcharrefreplace')
     #manage bug of hash generation for twitter and other api with query searches instead of standard uri
     if full_uri.find("//") > -1:
         obj_uri=urlparse.urlparse(full_uri)
         to_hash_uri=urllib.quote(obj_uri.scheme + "://" + obj_uri.netloc + obj_uri.path)

     else:
         #if uri not detected hash directly the query
         to_hash_uri=urllib.quote(full_uri)
     hasher.update(to_hash_uri)
     item_id=hasher.hexdigest()
     print "ES creation generated ID:"+item_id+"\r\nfor: "+to_hash_uri
     return item_id

# class CustomFlask(Flask):
#     """ Custom module of Flask which allow to include static_folder definition from config object """
#     def __init__(self,name):
#         super(Flask,self).__init__(name)
#
#     @property
#     def static_folder(self):
#         """ function to return static_folder as a property
#         :returns: static_folder path
#         """
#         if self.config.get('STATIC_FOLDER') is not None:
#             return os.path.join(self.root_path,
#                 self.config.get('STATIC_FOLDER'))
#
#     @static_folder.setter
#     def static_folder(self, value):
#         """ function to set static_folder path
#         :param str value: static_folder path
#         :returns: html
#         """
#         self.config['STATIC_FOLDER'] = value

#see However since the URL rule is still created in __init__ this only work for setting a different path, not for disabling it completely with None.
app = Flask(__name__,static_folder='static')
""" Using FLASK Framework """

config = app.config
if module_exists('default_settings'):
    config.from_object('default_settings.DevelopmentConfig')
else:
    config.from_object('dfm.default_settings.DevelopmentConfig')
if os.getenv('DFM_SETTINGS'):
    config.from_envvar('DFM_SETTINGS')
if os.path.isfile('settings.cfg'):
    config.from_pyfile('settings.cfg')

# memory limit
limit_memory(config['MEMORY_LIMIT'])

#auto = Autodoc(app)
api = Api(app)
""" Flask Restful API """

storage=Storage(app.logger,config)
""" Using decoration class storage to manage ElasticSearch input/outputs """

#"""Virtual screen for real web browser use 800x600 virtual screen
#display = Display(visible=0, size=(800, 600))
#display.start()


@app.route('/')
def home():
    sources=storage.query({"query":{"type":{"value":"source"}}})[0]
    app.logger.debug("API: Sources List:"+json.dumps(sources))
    dic_source={}
    for source in sources['hits']['hits']:
        dic_source[source['_id']]=source['_source']['title']
    sources_topics_stats=storage.query({ "size":0, "query": { "bool" : { "must":[ { "type" : { "value" : "doc" } }, { "nested": { "path": "topics", "query": { "exists": { "field":"topics.label" } } } } ] } }, "aggs":{ "sources": { "terms" : { "field" : "_parent" }, "aggs" : { "topics" : { "nested" : { "path" : "topics" }, "aggs" : { "group_by_state": { "terms" : { "field" : "topics.label" }, "aggs": { "average_score": { "avg": { "field": "topics.score" } } } } } } } } } })[0]
    app.logger.debug("API: Prediction Summary:"+json.dumps(sources_topics_stats))
    i=0
    for sources in sources_topics_stats['aggregations']['sources']['buckets']:
        if sources_topics_stats['aggregations']['sources']['buckets'][i]['key'] not in dic_source:
            dic_source[sources_topics_stats['aggregations']['sources']['buckets'][i]['key']]="Orphan News for "+sources_topics_stats['aggregations']['sources']['buckets'][i]['key']
        sources_topics_stats['aggregations']['sources']['buckets'][i]['title']=dic_source[sources_topics_stats['aggregations']['sources']['buckets'][i]['key']]
        i+=1
    return render_template('index.html',content=sources_topics_stats)

@app.route('/sources')
def sources():
    return render_template('sources.html',content=None)

@app.route('/securitywatch')
def securitywatch():
    return render_template('securitywatch.html', content=None)

@app.route('/topics')
def topics():
    return render_template('topics.html',content=None)

@app.route('/models')
def models():
    return render_template('models.html',content=None)

@app.route('/doc')
@app.route('/doc/')
@app.route('/doc/<path:path>')
def documentation(path='index.html'):
    """ Flask return html sphinx doc via /doc path

    :param str path:
    :returns: html
    """

    if request.path == '/doc':
        return redirect(request.url+'/index.html',code=302)
    else:
        return send_from_directory(config['DOC_PATH'],path)

def output_xml(data, ):
    resp = Response(data, mimetype='text/xml')
    return resp

def make_external(url):
    return urljoin(request.url_root, url)

def overall_score(es_score, topics_scores):
    """Calculation of overal__score of news based on OVERALL_SCORE_CALCULATION setting variable.

    :param float es_score: returned ElasticSearch query score for the news
    :param list scores: returned probabilities of predictied topics for the news in a list of float
    :returns: float overall score for the news calculated via setting variable above.
    """

    return eval(config['OVERALL_SCORE_CALCULATION'])

#@profile
@app.route('/atom.xml')
def recent_feed():
    """ Homepage RSS Feed is Top news for last 7days Number of news is defined by configuration

    :param str model: news source identifier
    :param str topic: topic in the model
    :param str q:  elasticsearch simple query string (https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html)
    :param str gte: greater date (default now-7d)
    :param str lte: liter date (default now)
    :param int offset: offset of news result (default 0)
    :param int size: number of news to retrieve (default settings ATOM_SIZE)
    :returns: atom rss feed
    """
    if request.args.get('model'):
        model=request.args.get('model').lower()
    else:
        model=None

    if request.args.get('topic'):
        topic=request.args.get('topic')
    else:
        topic=None

    if request.args.get('q'):
        q=request.args.get('q')
    else:
        q=None

    if request.args.get('gte'):
        gte=request.args.get('gte')
    else:
        gte='now-7d'

    if request.args.get('lte'):
        lte=request.args.get('lte')
    else:
        lte='now'

    if request.args.get('offset'):
        offset=request.args.get('offset')
    else:
        offset='0'

    if request.args.get('size'):
        size=request.args.get('size')
    else:
        size=config['ATOM_SIZE']

    app.logger.debug("ATOM RSS Feed parameters received: model="+str(model)+" topic="+str(topic)+" q="+str(q)+" gte="+str(gte)+" lte="+str(lte)+" offset="+str(offset)+" size="+str(size))

    #query by default
    time_range_query={ "sort" : [ { "topics.score" : { "order" : "dsc", "nested_path" : "topics" } }, { "updated" : { "order" : "dsc" } }, "_score" ], "query":{ "bool" : { "must":[ { "range" : { "updated" : { "gte" : gte, "lt" :  lte } } }, { "nested": { "path": "topics", "query": { "exists": { "field":"topics.label" } } } }, { "type":{ "value":"doc" } }] } } }

    if model or topic:
        model_query={"query" : { "constant_score" : { "filter" : { "bool" : { "must":[{ "type":{ "value":"model" } }] } } } } }
        if model:
            model_query["query"]["constant_score" ]["filter"]["bool"]["must"].append({ "term" : { "title" : model.lower() } })
        app.logger.debug("Models query: "+json.dumps(model_query))
        models=storage.query(model_query)[0]
        app.logger.debug("API: Prediction Models List:"+json.dumps(models))
        topics_query={ "nested": { "path": "topics", "query": { "bool" : { "should":[] } } } }
        for curr_model in models["hits"]["hits"]:
            app.logger.debug("Current Model: "+json.dumps(curr_model))
            for curr_topic in curr_model["_source"]["related_topics"]:
                app.logger.debug("Current Topic: "+curr_topic)
                if topic:
                    app.logger.debug("Topic as parameter: "+topic)
                    if curr_topic.lower()==topic.lower():
                        app.logger.debug("Topic match")
                        topics_query["nested"]["query"]["bool"]["should"].append({ "term" : { "topics.label" : curr_topic } })
                else:
                    topics_query["nested"]["query"]["bool"]["should"].append({ "term" : { "topics.label" : curr_topic } })

        app.logger.debug("Topics query: "+json.dumps(topics_query))
        time_range_query["query"]["bool"]["should"]=[topics_query]

    if q:
        app.logger.debug("Q query: "+json.dumps(q))
        time_range_query["query"]["bool"]["must"].append({"query_string" : {"query" : q}})

    if int(offset)>0:
        time_range_query['from']=offset
    if int(size)>-1:
        time_range_query['size']=size
    app.logger.debug(time_range_query)
    app.logger.debug("rss atom export")
    start_time = time.time()
    feeder = AtomFeed('Recent Articles',feed_url=request.url, url=request.url_root)
    docs=storage.query(time_range_query)[0]['hits']['hits']
    for doc in docs:
        if isinstance(doc, list):
            doc=doc[0]
        news=doc['_source']
        topics=[]
        scores=[]
        overall_scr=0
        if 'topics' in news:
            text_topics=""
            for topic in news['topics']:
                topics.append({"term":"_"+topic['label'],"label":topic['label']})
                scores.append(float(topic['score']/100))
                text_topics+="; "+topic['label']+":"+str(topic['score'])
            overall_scr=overall_score(doc['_score'],scores)
        else:
            overall_scr=0
        if 'tags' in news:
            for tag in news['tags']:
                topics.append({"term":tag,"label":tag})
        if len(news['summary']) < 5:
            news['summary']="No summary"
        if 'title' not in news or len(news['title'])<5:
            news['title']=news['summary']
        if 'author' not in news:
            news['author']="unknown"
        if 'updated' not in news:
            news['updated']=datetime.datetime.strptime(datetime.datetime.now(),'%Y-%m-%dT%H:%M:%S')
        elif type(news['updated'])==list:
            news['updated']=datetime.datetime.strptime(news['updated'][0][:19],'%Y-%m-%dT%H:%M:%S')
        else:
            news['updated']=datetime.datetime.strptime(news['updated'][:19],'%Y-%m-%dT%H:%M:%S')

        if overall_scr >= config['OVERALL_SCORE_THRESHOLD']:
            news['overall_score']=overall_scr
            # Dates with two different format on timezon (???)
            #'%Y-%m-%dT%H:%M:%SZ'
            #'%Y-%m-%dT%H:%M:%S+%z'
            #So timezone has been removed
            feeder.add(title=news['title'],title_type='text',summary=news['summary'],summary_type='text',content=news['content'],content_type='text',categories=topics,feed_url=make_external('/atom'),author=news['author'],url=urllib2.unquote(news['link']),updated=news['updated'],published=news['updated'],rights=text_topics,rights_type='text')
    feeder_response=feeder.get_response()
    feeder_response.headers["Content-Type"] = "text/xml"
    return feeder_response



class Main(Resource):
    """ Main page of the API / """

    def get(self):
        """ Default method to get list of existings sources

        :returns: json list of sources with their settings
        """
        return storage.query({"query":{"type":{"value":"source"}}})[0]

    def put(self):
        """ Add a source to ElasticSearch

        :param json data:  PUT method data field in json format
        :returns: json source settings with generated id
        """
        app.logger.debug(request.json)
        return storage.put(type="source",data=request.json)

class ObjectDetail(Resource):
    """ Manage object from it IDs """

    def __init__(self):
        super(Resource, self).__init__()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('type',default="doc")
        self.parser.add_argument('parent',default=None)
        self.args = self.parser.parse_args()

    def get(self, src_id):
        """ get settings of an Object from it ID

        :param string src_id: Object identifier
        :returns: json source settings
        """

        return storage.get(src_id)[0]

    def put(self, src_id):
        """ update object

        :param str src_id: Object identifier
        :param json data: PUT method data field in json format
        :returns: json update result
        """
        app.logger.debug(request.data)
        return storage.put(type=self.args.get("type"),source=self.args.get("parent"),data=request.json)

    def delete(self, src_id):
        """ Delete object from it id

        :param str src_id: Object identifier
        :returns: json source settings with generated id
        """

        return storage.delete(src_id, parent=self.args["parent"])

class DocList(Resource):
    """ List doc (news) for a given source """
    def __init__(self):
        super(Resource, self).__init__()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('format',default="json")
        self.parser.add_argument('from',default="now-7d")
        self.parser.add_argument('to',default="now")
        self.parser.add_argument('offset',default="0")
        self.parser.add_argument('size',default="-1")
        self.args = self.parser.parse_args()

    def get(self, src_id,format="json"):
        """ get news from a source

        :param str src_id: source identifier
        :param str format: requested format could be json or csv or atom
        :param str from: from date or relative date eg: now-7d
        :param str to: to date or relative date eg: now
        :param str offset: from offset eg: 0
        :param str size: extract number of news eg: 10000
        :returns: news list with details
        """
        app.logger.debug(src_id)
        gte=self.args['from']
        lte=self.args['to']
        offset=self.args['offset']
        size=self.args['size']
        app.logger.debug("parameters: \r\nid source: "+src_id+"\r\ngte: "+gte+"\r\nlte: "+lte+"\r\noffset: "+offset+"\r\nsize: "+size)
        time_range_query={ "sort" : [ { "topics.score" : { "order" : "dsc", "nested_path" : "topics" } }, { "updated" : { "order" : "dsc" } }, "_score" ], "query":{ "bool" : { "must":[ { "range" : { "updated" : { "gte" : gte, "lt" :  lte } }}] } } }
        if int(offset)>0:
            time_range_query['from']=offset
        if int(size)>-1:
            time_range_query['size']=size
        if src_id:
            time_range_query["query"]["bool"]["must"].append({"constant_score" : { "filter" : { "term" : { "origin" : src_id } } }})
        app.logger.debug(time_range_query)
        if self.args['format'] == "json":
            app.logger.debug("json direct export")
            result=storage.query(time_range_query)[0]
            app.logger.debug("API: Source's News:"+json.dumps(time_range_query))
            return result
        elif self.args['format'] == "csv":
            app.logger.debug("csv export")
            start_time = time.time()
            csv_output = io.BytesIO()
            writer = csv.writer(csv_output, delimiter='|',quotechar='`',quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["collector_id","news_id","updated_date","link","title","summary","overall_score","_score"])
            result_csv=storage.query(time_range_query)[0]['hits']['hits']
            app.logger.debug("API: Source's News:"+json.dumps(time_range_query))
            for doc in result_csv:
                if isinstance(doc, list):
                    doc=doc[0]
                app.logger.debug("fetch: "+doc['_source']['link'])
                updated=doc['_source']['updated']
                link=urllib2.unquote(doc['_source']['link'])
                title=doc['_source']['title']
                summary=doc['_source']['summary']
                topics=[]
                scores=[]
                overall_scr=0
                try:
                   for topic in doc['_source']['topics']:
                       topics.append(topic['label'])
                       topics.append(str(topic['score']))
                       scores.append(float(topic['score']/100))
                   overall_scr=overall_score(doc['_score'],scores)
                   app.logger.debug("overall_score: "+str(overall_scr))
                except:
                  app.logger.debug("ERROR no prediction")
                row=[doc['_parent'],doc['_id'],updated,link,title,summary,overall_scr,doc['_score']]
                row=row+topics
                app.logger.debug("write row: "+row[1])
                writer.writerow(row)
            app.logger.debug("csv export duration:"+str(time.time()-start_time))
            del row,updated,summary,topics,scores,overall_scr,link,gte,lte,offset,size,start_time
            gc.collect()
            return csv_output.getvalue()

class DocDetail(Resource):
    """ Doc (news) details provider """
    def get(self, src_id,doc_id):
        """ get one news

        :param str src_id: source identifier
        :param str news_id: news identifier
        :returns: json return result
        """
        return storage.get(parent=src_id,item_id=doc_id)[0]

    def put(self, src_id,doc_id):
        """ add or update one news

        :param str src_id: source identifier
        :param str news_id: news identifier
        :param json data: put data which contain update for the news
        :returns: json return result
        """
        if not request.json:
            abort(400)
        app.logger.debug("PUT src_id:"+src_id+" doc_id:"+doc_id+" link:"+request.json['link'])
        return storage.put(item_id=doc_id,type='doc',source=src_id,data=request.json)

#@profile
def multithreaded_processor(qid,query,doc_type='doc',content_crawl=True,content_predict=True,size=None):
    """ Multithreading task management
    from ES query process docs for multiple task in multithreading like crawl, predict, gather content.
    :param str type of ES documents (doc,source,model,topic)
    :param str query ES query to get docs
    :param bool content_crawl crawl doc contents on internet
    :param bool content_predict predict topics for docs from deepdetect
    :param int size batch size for ES query
    :result json return result
    """
    results=Results(app.logger,current=str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
    workers = multiprocessing.cpu_count()+1
    if not config['THREADED']:
        workers=1
    work_queue = Queue()
    done_queue = Queue()
    processes = []
    if size is not None:
        query['size']=size
    docs=storage.query(query)[0]['hits']
    results.set_total(docs['total'])
    count_docs=0
    for doc in docs['hits']:
        if isinstance(doc, list):
            for do in doc:
                work_queue.put(do)
                #results.add_success({'url':do['_source']['link'],'message':'added to processing queue','queue_size':work_queue.qsize()})
        else:
            work_queue.put(doc)
            #results.add_success({'url':doc['_source']['link'],'message':'added to processing queue','queue_size':work_queue.qsize()})

    for w in xrange(workers):
        p = Process(target=crawl, args=(doc_type,work_queue, done_queue, content_crawl, content_predict, ))
        p.start()
        processes.append(p)
        work_queue.put(None)

    for p in processes:
        p.join()

    done_queue.put(None)
    result=done_queue.get()

    if result != None:
        if result['failed']==0:
            results.add_success(result)
            app.logger.debug(result)
        else:
            results.add_fail(result)
            app.logger.debug(result)
    else:
        results.add_fail(result)
        app.logger.debug(result)
    while result is not None:
        result=done_queue.get()
        app.logger.debug(result)
        if result!= None:
            if result['failed']==0:
                results.add_success(result)
                app.logger.debug(result)
            else:
                results.add_fail(result)
                app.logger.debug(result)
        else:
            results.add_fail(result)
            app.logger.debug(result)

    #del size, workers, work_queue, done_queue, processes, docs, count_docs
    gc.collect()
    results.finish()

    return results.results

#@profile
def crawl(doc_type,work_queue, done_queue, content_crawl=True,content_predict=True):
    """ Function for workers to crawl ES doc (source,doc,...) """
    results=Results(app.logger,work_queue.qsize(),str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
    multi_pos="begin_crawl"
    if doc_type!="source":
        feed=Feed({"_id":"dummy feed","_source":{"link":"http://dummy/feed","tags":[],"freq":30,"depth":2,"step":10000,"limit":10000,"topics":{},"summary":"Content Crawler","title":"Content Crawler","format":"tt-rss","predict":content_predict,"enable_content":content_crawl,"active":False}},app.logger,storage, config)
    items=[]
    item=work_queue.get()
    while item is not None:
        try:
            if doc_type=="source":
                app.logger.debug("Multithread: source detected")
                multi_pos="source_crawl"
                feed_result=storage.get(item['_id'])
                feed=Feed(feed_result[0],app.logger,storage,config)
                results.add_success(feed_result[1])
                result=feed.crawl()
                results.add_success(result)
                item=None
                del feed
            elif doc_type=="doc":
                app.logger.debug("Multithread: doc detected")
                multi_pos="doc crawl"
                if content_crawl:
                    app.logger.debug("Multithread: crawl detected")
                    multi_pos="content_crawl"
                    item_result=feed.get_content(item)
                    new_item=item_result[0]
                    if new_item!=None:
                        item=new_item
                        results.add_success(item_result[1])
                    else:
                        del new_item
                        results.add_fail(item_result[1])

                if content_predict and item is not None:
                    app.logger.debug("Multithread: prediction detected")
                    multi_pos="content_predict"
                    predictions=feed.do_predict(item['_source'])
                    item['_source']=predictions[0]
                    result=predictions[1]
                    results.add_success(result)

                if item is not None:
                    app.logger.debug("Multithread: item detected")
                    items.append(item)
                    results.add_success({'url':item['_source']['link'],'id':item['_id']})
            else:
                results.add_fail({"message":"Empty work_queue","size":work_queue.qsize()})
        except Exception as e:
             results.add_fail(e)

        if len(items)>config["BATCH_SIZE"]:
            app.logger.debug("Multithread: flush items")
            result=storage.bulk(items)
            results.add_success(result)
            del items
            gc.collect()
            items=[]

        item=work_queue.get_nowait()
    if len(items)>0:
        app.logger.debug("Multithread: flush items")
        result=storage.bulk(items)
        results.add_success(result)
        del items
        items=[]
    if doc_type!="source":
        del feed
    app.logger.debug('Multithread: stopping thread')
    done_queue.put(results.results)
    del items, work_queue, done_queue
    gc.collect()


#@profile
def generate_doc(curr_path,doc):
    with open(curr_path+"/"+doc['_parent']+"_"+doc['_id']+".txt", 'w') as f:
        curr_doc=""
        if "title" in doc['_source']:
            curr_doc+="\r\n"+doc['_source']['title']
        if "updated" in doc['_source'] and isinstance(doc['_source']['updated'],basestring):
            curr_doc+="\r\n"+doc['_source']['updated']
        if "content" in doc['_source']:
            curr_doc+="\r\n"+str(doc['_source']['content'])
        if "summary" in doc['_source']:
            curr_doc+="\r\n"+doc['_source']['summary']
        if "author" in doc['_source']:
            curr_doc+="\r\n"+doc['_source']['author']
        if "text" in doc['_source']:
            curr_doc+="\r\n"+doc['_source']['text']
        if "tags" in doc['_source']:
            curr_doc+="\r\n"+",".join(doc['_source']['tags'])
        if detect(curr_doc) == "en":
            f.write(curr_doc.encode('utf-8','ignore'))

class Schedule(Resource):
    """ Function to call scheduled task from an external scheduler (e.g. curl with crontab)

    :Crontab Examples:

    00 */2 * * * curl -XGET http://localhost:12345/api/schedule/SOURCE_ID
    00 */1 * * * curl -XGET http://localhost:12345/api/schedule/source_crawl
    00 04 * * * curl -XGET http://localhost:12345/api/schedule/content_crawl
    * * * * */1 curl -XGET http://localhost:12345/api/schedule/generate_models
    """
    def __init__(self):
        super(Resource, self).__init__()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('predict',default="false")
        self.parser.add_argument('id',default=None)
        self.parser.add_argument('size',default=None)
        self.args = self.parser.parse_args()

    #@profile
    def get(self, src_id):
        """ crawl one source

        :param str src_id: source identifier, if identifier is *source_crawl* it is a special keyword to crawl sources, *content_crawl* it is a special keyword to crawl missing content for all news, *generate_models* is a special .
        :returns: json return result
        """
        result=""
        start_time = time.time()

        if src_id=="generate_models":
            if self.args['id'] is not None:
                model_caller=ObjectDetail()
                models=[model_caller.get(self.args['id'])]
            else:
                app.logger.debug("generate models:"+src_id)
                models_settings=ModelsSettingsList()
                models=models_settings.get()["hits"]["hits"]

            topics_settings=TopicsSettingsList()
            topics=topics_settings.get()["hits"]["hits"]

            for model in models:
                app.logger.debug("model:"+model["_source"]["title"])
                #generate training set for the model
                training_path=config['TRAININGS_PATH']+os.path.sep+model["_source"]["title"]

		#delete training folder if exists to avoid conflicts with previous training set
                if os.path.exists(training_path):
                    shutil.rmtree(training_path)
                os.makedirs(training_path)

                for curr_topic in model["_source"]["related_topics"]:
                    app.logger.debug("topic:"+curr_topic)
                    topic_path=training_path+os.path.sep+curr_topic
                    if not os.path.exists(topic_path):
                        os.makedirs(topic_path)
                    count_docs=0
                    for scan_topic in topics:
                        if curr_topic == scan_topic["_source"]["title"]:
                            app.logger.debug("topic match:"+curr_topic)
                            for tag in scan_topic["_source"]["tags"]:
                                nb_tags=len(scan_topic["_source"]["tags"])
                                app.logger.debug("tag:"+tag)
                                current_tag_doc_query={"query":{ "bool": { "must": [ {"exists" : { "field" : "text" } }, {"type":{"value":"doc"}}, {'term': {'tags': tag}}]}}}
                                tag_doc_results=storage.query(current_tag_doc_query)[0]
                                app.logger.debug("API: Tags: "+tag+"="+str(len(tag_doc_results["hits"]["hits"])))
                                for doc in tag_doc_results["hits"]["hits"]:
                                    if count_docs>int(model["_source"]["limit"])/nb_tags:
                                        app.logger.debug("Exceed training model extraction tags limit:"+str(count_docs)+"/"+str(int(model["_source"]["limit"])/nb_tags))
                                        break
                                    if isinstance(doc,list) or isinstance(doc,types.GeneratorType):
                                        for sub_doc in doc:
                                            app.logger.debug("output_sub_doc:"+sub_doc["_source"]["link"])
                                            generate_doc(topic_path,sub_doc)
                                    else:
                                        app.logger.debug("output_doc:"+doc["_source"]["link"])
                                        generate_doc(topic_path,doc)
                                    count_docs+=1
                                if count_docs>int(model["_source"]["limit"]):
                                    app.logger.debug("Exceed training model extraction limit:"+str(count_docs)+"/"+model["_source"]["limit"])
                                    break
                #generate models from training set
                model_path=config['MODELS_PATH']+os.path.sep+model["_source"]["title"]

                #delete model folder if exists to avoid conflicts with previous model version
                if os.path.exists(model_path):
                    shutil.rmtree(model_path)
                os.makedirs(model_path)
		trainer_def={"model-repo":os.path.abspath(model_path),"training-repo":os.path.abspath(training_path),"sname":model["_source"]["title"]+"_trainer","tsplit":0.01,"base-lr":0.01,"clevel":False,"sequence":140,"iterations":50000,"test-interval":1000,"stepsize":15000,"destroy":True,"resume":False,"finetune":False,"weights":None,"nclasses":len(model["_source"]["related_topics"]),"documents":True,"batch-size":128,"test-batch-size":16,"gpuid":0,"mllib":"xgboost","lregression":False}

                mt=ModelTrainer(trainer_def,app.logger,config)
                app.logger.debug(mt.createMLTrainerService())
                app.logger.debug(mt.trainModel())
                app.logger.debug(mt.clearMLTrainerService())
                dd=DD(config['DEEP_DETECT_URI'])
                model_def={'repository':os.path.abspath(model_path)}
                parameters_input = {'connector':'txt'}
                parameters_mllib = {'nclasses':len(model["_source"]["related_topics"])}
                parameters_output = {}
                try:
                    response=dd.delete(model["_source"]["title"])
                except:
                    app.logger.debug(model["_source"]["title"])
                retry=0
                while model["_source"]["title"] in dd.info():
                    time.sleep(5)
                    app.logger.debug("Waiting for DeepDetect service removal:"+model["_source"]["title"])
                    retry+=1
                    if retry>10:
                        break
                app.logger.debug("dd.put_service("+model["_source"]["title"]+","+str(model_def)+","+model["_source"]["summary"]+",xgboost,"+str(parameters_input)+","+str(parameters_mllib)+","+str(parameters_output)+", mltype='supervised')")
                result=dd.put_service(model["_source"]["title"],model_def,model["_source"]["summary"],"xgboost",parameters_input,parameters_mllib,parameters_output, mltype='supervised')
                app.logger.debug(result)
        elif src_id=="sources_crawl":
            app.logger.debug("sources crawl:"+src_id)
            """ Crawl all sources to update news list and meta-data
            :returns: json return result
            """
            app.logger.debug("sources crawl:"+src_id)
            query={ "query":{ "bool": { "must": [ {"type":{"value":"source"}} ]}}}
            if request.args.get('id')!=None:
                query['query']['bool']['must'].append({"ids":{"type":"doc","values":self.args.get('id').split(',')}})
            if request.args.get('size')!=None:
                query['size']=int(self.args.get('size'))
            result=multithreaded_processor(src_id,query,doc_type='source',content_crawl=False,content_predict=False)

        elif src_id=="contents_crawl":
            app.logger.debug("contents crawl:"+src_id)
            query={ "query":{ "bool": { "must": [ {"missing" : { "field" : "text" } }, {"type":{"value":"doc"}} ]}}}
            if request.args.get('id')!=None:
                query['query']['bool']['must'].append({"ids":{"type":"doc","values":self.args.get('id').split(',')}})
            if request.args.get('size')!=None:
                query['size']=int(self.args.get('size'))
            result=multithreaded_processor(src_id,query,doc_type='doc',content_crawl=True,content_predict=True)

        elif src_id=="contents_predict":
            app.logger.debug("predict contents:"+src_id)
            """ Predict all contents in the database
            :returns: json return result
            """
            query={ "query":{ "bool": { "must": [ {"exists" : { "field" : "text" } }, {"type":{"value":"doc"}} ]}}}
            if request.args.get('id')!=None:
                query['query']['bool']['must'].append({"ids":{"type":"doc","values":self.args.get('id').split(',')}})
            if request.args.get('size')!=None:
                query['size']=int(self.args.get('size'))
            result=multithreaded_processor(src_id,query,doc_type='doc',content_crawl=False,content_predict=True)

        else:
            app.logger.debug("crawl source:"+src_id)
            feed=Feed(storage.get(src_id)[0],app.logger,storage,config)
            result+=str(feed.crawl())
            del feed

        gc.collect()
        return {"source":src_id,"result":result,"duration":(time.time()-start_time)}

class VoidReturn(Resource):
    def get(sef):
        return {"void":"None"}

class TagsList(Resource):
    """ Return list of tags provided by news sources """
    def __init__(self):
        super(Resource, self).__init__()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('size',default="10")
        self.args = self.parser.parse_args()

    def get(self):
        """ provide tags and count of news by tag
        This function use elasticsearch aggregation by term on field tags
        More details: https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-terms-aggregation.html#_size

        :param str size: extract number of results default: 10
        :returns: json return result
        """
        result_size=self.args['size']
        #tags with topics required query
        #query={ "size":0, "query": { "bool" : { "must":[ { "type" : { "value" : "doc" } }, { "nested": { "path": "topics", "query": { "exists": { "field":"topics.label" } } } } ] } }, "aggs":{ "sources": { "terms" : { "field" : "_parent" }, "aggs" : { "group_by_state": { "terms" : { "field" : "tags", "size" : result_size } } } } } }
        query={ "size":0, "query": { "bool" : { "must":[ { "type" : { "value" : "doc" } } ] } }, "aggs":{ "group_by_state": { "terms" : { "field" : "tags", "size" : result_size } } } }
        return storage.query(query)[0]

class TopicsSettingsList(Resource):
    """ Manage list of topics settings to generate datasets for models training """

    def get(self):
        """ Default method to get list of existings topics settings

        :returns: json list of topics settings with their settings
        """

        return storage.query({"query":{"type":{"value":"topic"}}})[0]

    def put(self):
        """ Add a topics settings to ElasticSearch

        :param json data:  PUT method data field in json format
        :returns: json source settings with generated id
        """

        return storage.put(type="topic",data=request.json)

class TopicsSettingsDetail(Resource):
    """ Show settings of a topic """

    def get(self, src_id):
        """ get settings of a topic

        :param string src_id: topic identifier
        :returns: json topic settings
        """

        return storage.get(src_id)[0]

    def put(self, src_id):
        """ update topic settings

        :param str src_id: Topic identifier
        :param json data: PUT method data field in json format
        :returns: json update result
        """

        return storage.update(item_id=src_id,type="topic",data=request.json)

class TopicsList(Resource):
    """ Return list of topics predicted by Deep Detect """
    def __init__(self):
        super(Resource, self).__init__()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('size',default="10")
        self.args = self.parser.parse_args()

    def get(self):
        """ provide topics and count of news by topics
        This function use elasticsearch aggregation by term on field tags
        More details: https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-terms-aggregation.html#_size

        :param str size: extract number of results default: 10
        :returns: json return result
        """
        result_size=self.args['size']
        query={ "size":0, "query": { "bool" : { "must":[ { "type" : { "value" : "doc" } }, { "nested": { "path": "topics", "query": { "exists": { "field":"topics.label" } } } } ] } }, "aggs":{ "sources": { "terms" : { "field" : "_parent" }, "aggs" : { "topics" : { "nested" : { "path" : "topics" }, "aggs" : { "group_by_state": { "terms" : { "field" : "topics.label", "size" : result_size }, "aggs": { "average_score": { "avg": { "field": "topics.score" } } } } } } } } } }
        return storage.query(query)[0]

class ModelsList(Resource):
    """ Return list of models ready in Deep Detect """
    def __init__(self):
        super(Resource, self).__init__()
        self.dd=DD(config['DEEP_DETECT_URI'])

    def get(self):
        """ List models available in Deep Detect
        :returns: json return result
        """
        return self.dd.info()['head']['services']

class ModelsSettingsList(Resource):
    """ Manage list of models settings to generate datasets of multiple topics for training """

    def get(self):
        """ Default method to get list of existings models settings

        :returns: json list of models settings with their settings
        """

        return storage.query({"query":{"type":{"value":"model"}}})[0]

    def put(self):
        """ Add a model settings to ElasticSearch

        :param json data:  PUT method data field in json format
        :returns: json source settings with generated id
        """

        return storage.put(type="model",data=request.json)

class ModelsSettingsDetail(Resource):
    """ Show settings of a model """

    def get(self, src_id):
        """ get settings of a model

        :param string src_id: model identifier
        :returns: json model settings
        """

        return storage.get(src_id)[0]

    def put(self, src_id):
        """ update model settings

        :param str src_id: Model identifier
        :param json data: PUT method data field in json format
        :returns: json update result
        """

        return storage.update(item_id=src_id,type="model",data=request.json)

class TrainingsStatsList(Resource):

    """ Count number of docs by Topics usable for Models Training """

    def get(self):
        """ Default method to get number of training doc by topic

        :returns: json list of topics with number of docs usable for model training
        """

        topics_settings=TopicsSettingsList()
        topics_list=topics_settings.get()
        result={"docs": {"topics": {"buckets": [] } }}

        for topic in topics_list["hits"]["hits"]:
            topic_stats={ "doc_count": 0, "key":topic["_source"]["title"], "_id":topic["_id"]}
            for tag in topic["_source"]["tags"]:
                #current_tag_doc_query={"query":{ "bool": { "must": [ {"exists" : { "field" : "text" } }, {"type":{"value":"doc"}}, {'term': {'tags': tag}}]}}}
                current_tag_doc_query={ "size": 0, "aggs": { "tag": { "filter": { "bool": { "must": [ { "exists": { "field": "text" } }, { "type": { "value": "doc" } }, { "term": { "tags": tag } } ] } } } } }
                tag_doc_results=storage.query(current_tag_doc_query)[0]
                #topic_stats["doc_count"]+=tag_doc_results["hits"]["total"]
                topic_stats["doc_count"]+=tag_doc_results["aggregations"]["tag"]["doc_count"]
            result["docs"]["topics"]["buckets"].append(topic_stats)

        return result

class ChromePlugin(Resource):

    """ No need for it at the moment

    def get(self):
    """

    """ Method used to submit urls from the chrome ChromePlugin

    :returns: json result
    """

    def put(self):
        data=request.json
        dfm_api_base=data[dfm]
        source_uuid=generate_uuid('/api/chromeplugin')
        news_uuid=generate_uuid(data['link'])
        keywords=data['keywords']
        doc= {}

        doc["origin"] = source_uuid
        doc["updated"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        doc["format"] = "chromeplugin"
        if len(keywords)>0:
            doc["tags"] = keywords
        doc["source_type"] = "chromeplugin"
        doc["link"] = data['link']
        doc["source"] = data['first_name']+" "+data['lastname']
        print json.dumps(doc)

        response = http.request('GET',dfm_api_base+source_uuid+"/"+news_uuid)
        print "GET "+dfm_api_base+source_uuid+"/"+news_uuid+" status:"+str(response.status)
        result_doc=json.loads(response.data)

        if result_doc['found'] and 'text' in result_doc['_source']:
            if len(keywords)==0:
                return result_doc

        max_retry=5
        retries=0
        text=False
        while not text:
            print "waiting for body text..."
            response = http.urlopen('PUT',dfm_api_base+source_uuid+"/"+news_uuid, headers={'content-type': 'application/json'},body=json.dumps(doc))
            print "PUT "+dfm_api_base+source_uuid+"/"+news_uuid+" status:"+str(response.status)
            #print response.data

            response = http.request('GET',dfm_api_base+"schedule/contents_crawl?id="+news_uuid) #auth=('user', 'password'))
            print "GET "+dfm_api_base+"schedule/contents_crawl?id="+news_uuid+" status:"+str(response.status)
            #print response.data

            response = http.request('GET',dfm_api_base+source_uuid+"/"+news_uuid)
            print "GET "+dfm_api_base+source_uuid+"/"+news_uuid+" status:"+str(response.status)
            #print response.data
            result_doc=json.loads(response.data)
            retries+=1

            if '_source' in result_doc:
                if 'text' in result_doc['_source']:
                    text=True
                    print "body text found!"

            if retries>max_retry:
                print "MAX RETRY EXIT"
                break
        if '_source' in result_doc:
            if 'html' in result_doc:
                result_doc['_source'].pop('html')
        return result_doc

#Class attachments to API URIs
api.add_resource(Main, '/api')
api.add_resource(TagsList, '/api/tags')
api.add_resource(TopicsList, '/api/topics')
api.add_resource(ModelsList, '/api/models')
api.add_resource(TopicsSettingsList, '/api/topics/config',endpoint='topicssettings')
api.add_resource(TrainingsStatsList, '/api/trainings',endpoint='trainingsstats')
api.add_resource(ModelsSettingsList, '/api/models/config',endpoint='modelssettings')
api.add_resource(Schedule, '/api/schedule/<string:src_id>',endpoint='single_schedule')
api.add_resource(ObjectDetail, '/api/<string:src_id>/config',endpoint='config')
api.add_resource(TopicsSettingsDetail, '/api/topics/<string:src_id>/config',endpoint='topicssettingsdetail')
api.add_resource(ModelsSettingsDetail, '/api/models/<string:src_id>/config',endpoint='modelssettingsdetail')
api.add_resource(DocList, '/api/<string:src_id>/',endpoint='docs')
api.add_resource(DocDetail, '/api/<string:src_id>/<string:doc_id>',endpoint='doc')
api.add_resource(VoidReturn, '/favicon.ico',endpoint='favicon')
api.add_resource(ChromePlugin, '/api/chromeplugin')

if __name__ == '__main__':
    #Logging format hide console pin and flask default message
    # Comment next 4 lines to display pin console in logs
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s' , datefmt='%m/%d/%Y %I:%M:%S %p')
    handler = RotatingFileHandler(config['LOG_PATH'], maxBytes=10000, backupCount=1)
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    app.run(threaded=config['THREADED'],host=config['LISTEN_MASK'],port=config['LISTEN_PORT'])
