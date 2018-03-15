#!/usr/bin/env python2
# -*- coding: utf-8 -*-
""" Config can be set via 3 modes:
( according to http://flask.pocoo.org/docs/0.10/config/ )
1. by module dfm.default_settings
2. by environment variable DFM_SETTINGS
3. by settings.cfg file detected in execution folder
Priority of setting is given by number above.
Config in *3.* will overwrite config in *2.* and *1.* .
"""
import os

class Config(object):
    """ Default config class for all environments
    """
    DEBUG = False
    """ Enable DEBUG Level """
    TESTING = False
    """ Enable TESTING Level """
    MEMORY_LIMIT=int(os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')/2)
    """ Set memory limit for DFM by default Limit is half of total memory size """
    ES_URIS = ['http://localhost:9200']
    """ Set proxy if required to access ElastiSearch (could become global variable in the futur)
    syntax: {'https': 'http://proxy.adress:port' }
    """
    ES_PROXY = None
    """ ElasticSearch REST API URLs """
    ES_INDEX = 'watch'
    """ ElasticSearcg index name """
    ES_TIMEOUT = 180
    """ ElasticSearch queries timeout """
    ES_SEARCH_CACHING_DELAY = "1h"
    """ ElasticSearch large query (scroll) caching time, 1h is 1 hour """
    ES_BATCH_SIZE = 1000
    """ ElasticSearch batch size """
    BATCH_SIZE = 1000
    """ DFM batch size for queue management"""
    MEM_RATIO=0.5
    """ DFM memory limit as ratio of total hardware memory """
    DOC_PATH = os.path.join(os.path.dirname(__file__), "../doc/_build/html")
    """ DFM documentation local path """
    BROWSER_PATH = os.path.join(os.path.dirname(__file__), "../utils/browser")
    """ DFM documentation local path """
    LOG_PATH = 'dfm.log'
    """ DFM log file path """
    STATIC_FOLDER = 'static'
    """ DFM static pages local path """
    TWITTER_CONSUMER_KEY = ''
    """ TWITTER OAuth consumer key """
    TWITTER_CONSUMER_SECRET = ''
    """ TWITTER OAuth consumer secret """
    TWITTER_ACCESS_TOKEN = ''
    """ TWITTER OAuth access token """
    TWITTER_ACCESS_SECRET = ''
    """ TWITTER OAuth access secret """
    DEEP_DETECT_URI = 'localhost'
    """ Deep Detect rest api URI """
    DEEP_DETECT_PORT = 'localhost'
    """ Deep Detect rest api PORT """
    TRAININGS_PATH = '../training'
    """ Path used to generate trainings for models """
    MODELS_PATH = '../models'
    """ Type of model to train in deep detect, could be caffe or xgboost """
    MODEL_TYPE = "xgboost"
    """ Use GPU to train the model (available only for caffee)? """
    MODEL_GPU = False
    """ Path used to stored model generated by deepdetect """
    TOPICS_PREDICTION = True
    """ Enable Deep Detect Topics prediction """
    STORE_HTML=True
    """ Store raw html of news """
    NEWS_MIN_TEXT_SIZE=1000
    """ Minimum characters which must be present in a news to be imported """
    FAST_CRAWLING_MODE=True
    """ Drop all web pages which can not be collected fastly and easily,
    *WARNING*:disable FAST_CRAWLING_MODE still experimental the slow mode use PhantomJS which is knowed to have unfixed memory leaks.
    """
    CRAWLING_POOL_CONNECTIONS=10
    """ Number of concurrent connections during crawling of a feed """
    CRAWLING_RETRIES=5
    """ Max number of url retry """
    CRAWLING_REDIRECTS=5
    """ Max number of url redirect """
    CRAWLING_TIMEOUT_CONNECT=5.0
    """ url connection timeout """
    CRAWLING_TIMEOUT_READ=10.0
    """ url read timeout """
    CRAWLING_USERAGENT="Googlebot-News"
    """ Define user agent for crawler more examples at https://support.google.com/webmasters/answer/1061943?hl=en or http://www.useragentstring.com/pages/useragentstring.phphttp://www.useragentstring.com/pages/useragentstring.php """
    BROWSER_CRAWLING=False
    """ Enable crawling with PhantomJS and Chromium (commented currently) """
    #SERVER_NAME='localhost'
    # DFM server hostname setting DEPRECATED
    LISTEN_MASK='0.0.0.0'
    """ Mask subnet range to listen for requests """
    LISTEN_PORT=12345
    """ Listen port for requests """
    THREADED=True
    """ DFM is multi-threaded is True """
    ATOM_SIZE='4000'
    """ RSS ATOM Generated feed number of max news presented """
    NODES_SIZE='14'
    """ GRAPH Generated size by type of nodes """
    OVERALL_SCORE_THRESHOLD=0.1
    """ News rank threshold for RSS ATOM Generated feed """
    OVERALL_SCORE_CALCULATION="es_score*(sum(topics_scores)/len(topics_scores))"
    """ Method for calculating oaverall_score about news ranking
       python math formula to process evaluated during score calculation.
       parameters are: es_score (ElasticSearch given score in float for the news), topics_scores (Predicted topics scores in a list of float)
       scores are between 0 and 1 float values.
       :examples: 'es_score*(sum(topics_scores)/len(topics_scores))', 'log(1+score(ES))*(sum(topics_scores)/len(topics_scores))'
    """
    EXCLUDED_FILE_EXTENSIONS=[r'\.iso',r'\.mp3',r'\.mp4',r'\.bin',r'\.rom',r'\.zip',r'\.tar',r'\.tgz',r'\.xz',r'\.img']
    """List of files extensions to exclude from contents crawl"""
    EXCLUDED_URIS=[r'sourceforge\.net']
    """ List urls which as to be excluded from crawl """

class ProductionConfig(Config):
    """ Default config class for production environments
    """

class DevelopmentConfig(Config):
    """ Default config class for development environments
    """

    DEBUG = True

class TestingConfig(Config):
    """ Default config class for testing environments
    """
    TESTING = True
