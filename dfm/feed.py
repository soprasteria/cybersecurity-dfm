#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"Data Feed Manager Feed object used to crawl, extract content for one feed"
import re
import sys
import os
import signal
import inspect
import tempfile

from memory_profiler import profile
import base64
import json
import signal
import gc

from datetime import datetime, timedelta
import time

import feedparser
import urllib3, urllib2
#httplib, urlparse, requests
from urllib3.exceptions import TimeoutError, ConnectionError, ConnectTimeoutError, MaxRetryError
from httplib import HTTPException
from urllib2 import URLError


from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException, WebDriverException


import tweepy
from tweepy.error import TweepError
from tweepy import OAuthHandler

from newspaper import Article
from readability.readability import Document
from bs4 import BeautifulSoup
import magic
import textract

from langdetect import detect

#from dd_client import DD, DDCommunicationError
from dd_client import DD
""" Deep Detect client is mandatory for prediction """

from results import Results

class wait_for_page_load(object):

    def __init__(self, browser):
        self.browser = browser

    def __enter__(self):
        self.old_page = self.browser.find_element_by_tag_name('html')

    def page_has_loaded(self):
        new_page = self.browser.find_element_by_tag_name('html')
        return new_page.id != self.old_page.id

    def __exit__(self, *_):
        self.wait_for(self.page_has_loaded)

    def wait_for(self,condition_function):
        start_time = time.time()
        while time.time() < start_time + 15:
            if condition_function():
                return True
            else:
                time.sleep(0.1)
        raise Exception(
            'Timeout waiting for {}'.format(condition_function.__name__)
        )


    def click_through_to_new_page(self,link_text):
        browser.find_element_by_link_text('my link').click()

        def page_has_loaded():
            page_state = browser.execute_script(
                'return document.readyState;'
            )
            return page_state == 'complete'

        self.wait_for(page_has_loaded)

class Feed:
    """ Object to handle a news source (feed)
     to setup a source through rest api
     .. seealso:: :class:`Add a feed source`
    """
    def __init__(self,structure,logger,storage,config):
        """ Instanciate a feed (news source)
        :param dic structure: Feed (news source) specific settings
        :param obj logger: DFM logger object
        :param obj storage: DFM storage object
        :param obj config: DFM global config object
        :returns: Feed object (instance of a news source)
        """

        self.logger=logger
        self.structure=structure
        self.storage=storage
        self.config=config

        #https://coderwall.com/p/9jgaeq/set-phantomjs-user-agent-string
        #https://support.google.com/webmasters/answer/1061943?hl=en
        if not self.config['FAST_CRAWLING_MODE']:
            dcap = dict(DesiredCapabilities.PHANTOMJS)
            dcap["phantomjs.page.settings.userAgent"] = (config['CRAWLING_USERAGENT'])
            dcap["phantomjs.page.settings.resourceTimeout"] = ( "5000" )
            self.browser = webdriver.PhantomJS(service_log_path='/opt/dfm/ghostdriver.log',service_args=['--ignore-ssl-errors=true'],desired_capabilities=dcap)
            self.browser.set_page_load_timeout(5)
            self.browser.set_window_size(1120, 550)


        if "_id" not in self.structure:
            self.logger.debug(self.structure)
        else:
            self.id=self.structure["_id"]
        self.content=self.structure["_source"]["enable_content"]
        """ **enable_content** field crawl content if True """
        self.logger.debug("Content crawled enabled:"+str(self.content))

        predict_config=self.structure["_source"]["predict"]
        self.predict=predict_config and config['TOPICS_PREDICTION']
        """ if **predict** field and in DFM config **TOPICS_PREDICTION** are both true, DeepDetect prediction is called """
        self.logger.debug("Content prediction:"+str(self.predict))

        self.format=self.structure["_source"]["format"]
        """ field **format** define type of source
        which could be:
                     - **rss** RSS/ATOM source
                     - **tt-rss** TinyTiny RSS source
                     - **twitter** Twitter source
                     - **reddit** Reddit source
        """
        #bug legacy compliance issue #2
        self.limit=int(self.structure["_source"]["limit"])
        """ **limit** field define max size for a query to the source """
        #bug legacy compliance issue #2
        self.step=int(self.structure["_source"]["step"])
        """ **step** define offset incrementation for each query to the source """
        self.url=urllib2.unquote(self.structure['_source']['link'])
        """ **link** source uri, used also as data to generate unique internal id **_id** """

        self.twitter_consumer_key = self.config['TWITTER_CONSUMER_KEY']
        self.twitter_consumer_secret = self.config['TWITTER_CONSUMER_SECRET']
        self.twitter_access_token = self.config['TWITTER_ACCESS_TOKEN']
        self.twitter_access_secret = self.config['TWITTER_ACCESS_SECRET']

        self.min_text_size=self.config['NEWS_MIN_TEXT_SIZE']

        self.dd=DD(self.config['DEEP_DETECT_URI'])

        self.http=urllib3.PoolManager(num_pools=self.config['CRAWLING_POOL_CONNECTIONS'],timeout=urllib3.Timeout(connect=self.config['CRAWLING_TIMEOUT_CONNECT'], read=self.config['CRAWLING_TIMEOUT_READ']),retries=urllib3.Retry(self.config['CRAWLING_RETRIES'], redirect=self.config['CRAWLING_REDIRECTS']))

        self.url_validator=re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', flags=re.IGNORECASE|re.MULTILINE)

        self.uri_exclusion=self.config['EXCLUDED_URIS']
        self.file_extensions_exclusion=self.config['EXCLUDED_FILE_EXTENSIONS']

    def __exit__(self):
        """ Destroy all elements of the object before destroy the object to improve GC memory release """
        #https://github.com/seleniumhq/selenium/issues/767
        browser_pid=self.browser.binary.process.pid
        self.browser.service.process.send_signal(signal.SIGTERM)
        self.browser.quit()
        os.kill(browser_pid, signal.SIGTERM)
        del self.dd
        del self.url_validator
        del self.storage
        del self.structure
        del self.logger
        del self.config

    def crawl(self):
        """ Crawl the source
            based on field "format" in source settings
        """
        results=Results(self.logger,1,str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
        if self.format == "rss":
            result=self.standard_get(self.url)
        elif self.format == "tt-rss":
            result=self.ttrss_get()
        elif self.format == "twitter":
            result=self.twitter_get()
        elif self.format == "reddit":
            result=self.pligg_get()
        elif self.format == "doplhin":
            result=self.dolphin_get()
        elif self.format == "pligg":
            result=self.pligg_get()
        results.finish()
        return results.results

    #@profile
    def _feed_format_refactor(self,feed):
        """ format rss news to be compliant with doc (news) scheme """
        i=0
        results={'successfull':0,'fail':0,'took':0,'errors':[]}
        for entry in feed.entries:
            self.logger.debug("Collecting news num: "+str(i))

            if "tags" in entry:
                tags=[]
                for tag in feed.entries[i]['tags']:
                    tags.append(tag['term'])
                feed.entries[i]['tags']=tags
            if "updated" not in entry:
                feed.entries[i]["updated"]=time.time()
            if "source" in entry:
                feed.entries[i]['source']=entry['source']['link']
            else:
                feed.entries[i]['source']=""
            feed.entries[i]['origin']=self.id
            feed.entries[i]['format']="rss"
            feed.entries[i]['source_type']="rss"
            i+=1
        return feed

    #@profile
    def standard_get(self,url):
        """ rss feed (source) news collect """
        results=Results(self.logger,current=str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
        feed=feedparser.parse(url)
        feed=self._feed_format_refactor(feed)
        self.logger.debug("Collected "+str(len(feed.entries))+" entries")
        docs=[]
        if len(feed.entries)>0:

            for entry in feed.entries:
                #bulk helpers format http://elasticsearch-py.readthedocs.io/en/master/helpers.html#bulk-helpers
                doc={'_parent':self.id,'_routing':self.id,'_type':'doc','doc':entry}
                docs.append(doc)
            result=self.update(docs)
            results.add_success(result)
        else:
            results.add_fail({'url':url,'message':'No entries for this standard feed'})
        del feed
        gc.collect()
        return [docs,results.results]

    #@profile
    def ttrss_get(self):
        """ TinyTiny RSS news collect """
        results=Results(self.logger,current=str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
        docs=[]
        offset=0
        limit=self.limit
        url=self.url+"&offset="+str(offset)+"&limit="+str(limit)
        docs_results=self.standard_get(url)
        docs.append(docs_results[0])
        result=docs_results[1]
        if result['successful']>0:
            results.add_success({"url":url,"message":result})
        else:
            results.add_fail(result)
        while results.results['failed']==0:
            self.logger.debug(url)
            self.logger.debug("tt-rss offset="+str(offset)+" limit="+str(limit))
            docs.append(docs_results[0])
            result=docs_results[1]
            if result['successful']>0:
                results.add_success({"url":url,"message":result})
            else:
                results.add_fail({"url":url,"message":result})

            offset+=limit
            url=self.url+"&offset="+str(offset)+"&limit="+str(limit)
            docs_results=self.standard_get(url)
        return results.results

    #@profile
    def twitter_get(self):
        """ Twitter news collect, link are extracted from the twitts and manage as news """
        results=Results(self.logger,current=str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))

        auth = OAuthHandler(self.twitter_consumer_key, self.twitter_consumer_secret)
        auth.set_access_token(self.twitter_access_token, self.twitter_access_secret)

        #tweepy.debug(True)
        twt_api = tweepy.API(auth,retry_count=3,retry_delay=1,timeout=10,wait_on_rate_limit=True,wait_on_rate_limit_notify=True)
        ssearches=[]
        # gather stored seraches from your twitter account
        for ssearch in twt_api.saved_searches():
            ssearches.append(ssearch.query)
        #add search from current source
        ssearches.append(self.structure['_source']['link'])

        for ssearch in ssearches:
            result={}
            query={"fields":["id"],"from":0,"size":1,"query" : {"match":{"_parent":"848efa1a0badd5cfa5b07598067a526b"}},"sort" : [{"id" : {"order" : "dsc","mode" : "max"}}]}
            try:
               lastest_id=self.storage.query(query)[0]['hits']['hits'][0]['fields']["id"]
            except:
                lastest_id=0
            twitts=[]
            try:
                for raw_twitt in tweepy.Cursor(twt_api.search,q=ssearch,
                               count=self.structure['_source']['limit'],
                               result_type='recent',
                               #since=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                               #until=datetime.now().strftime("%Y-%m-%d"),
                               since_id=lastest_id,
                               include_entities=True,
                               monitor_rate_limit=True,
                               wait_on_rate_limit=True,
                               lang="en").items(self.limit):
                    twitt_link="https://twitter.com/"+raw_twitt.user.screen_name+"/status/"+raw_twitt.id_str
                    if raw_twitt.entities['urls'] and self.url_validator.match(raw_twitt.entities['urls'][0]['expanded_url']):


                        urls=[]
                        for curr_url in raw_twitt.entities['urls']:
                            if self.url_validator.match(curr_url['expanded_url']):
                                urls.append(curr_url['expanded_url'])
                        summary=re.sub('[a-z]+://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', raw_twitt.text, flags=re.MULTILINE)

                        self.logger.debug("Unshorting: "+urls[0])
                        twitt={"link":self.redirects_pass_through(urls.pop(0))}

                        hashtags=[]
                        for curr_hashtag in raw_twitt.entities['hashtags']:
                            hashtags.append(curr_hashtag['text'])
                        try:
                            lang_detect=detect(summary)
                        except Exception as e:
                            results.add_error(e)
                            lang_detect=""
                        twitt.update({
                         "origin":self.id,
                         "author": raw_twitt.user.screen_name,
                         "id": raw_twitt.id,
                         "related_links": urls,
                         "source_type":"twitter",
                         "format":"twitter",
                         "source": twitt_link,
                         "summary": summary,
                         "tags": hashtags,
                         "title": summary,
                         "content":[{"base":ssearch,"language":lang_detect}],
                         "updated": raw_twitt.created_at,
                         "occurences":raw_twitt.retweet_count,
                        })
                        #bulk helpers format http://elasticsearch-py.readthedocs.io/en/master/helpers.html#bulk-helpers
                        twitts.append({"_parent":self.id,"_routing":self.id,"_type":"doc","doc":twitt})
                        results.add_success(twitt_link)
                        del twitt
                    else:
                        results.add_fail({'url':twitt_link,'message':'No link in this twitt'})

                    #if (time.time()-start_time)>10:
                    #    break

            except tweepy.error.TweepError as e:
                results.add_error({'url':twitt_link,'message':str(e)})
            self.logger.debug("Pushing Twitts")
            result=self.update(twitts)
            results.add_success(result)
            del twitts

        del twt_api,ssearches
        gc.collect()
        results.finish()
        return results.results

    def pligg_get(self):
        """ not implemented yet """
        # self.logger.debug(self.url)
        # self.browser.get(self.url)
        #
        # news=[]
        # while True:
        #     time.sleep(3)
        #     self.logger.debug(browser.current_url)
        #     news_divs=browser.find_elements_by_xpath('//div[@class="stories"]')
        #     for news_div in news_divs:
        #         news_div_id=news_div.get_attribute('id')
        #         news_id=news_div.find_elements_by_xpath('//div[@id="'+news_div_id+'"]//h2/a')[0].get_attribute('href')
        #         news_link=news_id
        #         news_title=news_div.find_elements_by_xpath('//div[@id="'+news_div_id+'"]//h2/a')[0].get_attribute('textContent')
        #         news_summary=news_div.find_elements_by_xpath('//div[@id="'+news_div_id+'"]//div[@class="news-body-text"]')[0].get_attribute('textContent').replace('\n',"").replace('\t',"")
        #         news_tags=news_div.find_elements_by_xpath('//div[@id="'+news_div_id+'"]//i[@class="fa fa-tag"]/following-sibling::a')
        #         news_category=news_div.find_elements_by_xpath('//div[@id="'+news_div_id+'"]//i[@class="fa fa-folder"]/following-sibling::a')[0].get_attribute('textContent')
        #         news_source=news_div.find_elements_by_xpath('//div[@id="'+news_div_id+'"]//i[@class="fa fa-globe"]/following-sibling::a')[0].get_attribute('textContent')
        #         days_ago=re.search(' ([0-9]+) days ago',news_div.find_elements_by_xpath('//div[@id="'+news_div_id+'"]')[0].get_attribute('innerHTML'))
        #         #news_updated=time.asctime((datetime.now() - timedelta(days=int(days_ago.group(1)))).timetuple())
        #         news_tags_list=[news_category]
        #         #news_raw=urllib2.quote(browser.page_source.encode('utf-8','ignore'))
        #         news_author=""
        #
        #         for news_tag in news_tags:
        #             news_tags_list.append(news_tag.get_attribute('textContent'))
        #
        #         try:
        #             #subbrowser = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true'])
        #             #with wait_for_page_load(subbrowser):
        #             subbrowser.get(news_id)
        #             time.sleep(3)
        #             news_link=subbrowser.current_url
        #             self.logger.debug(news_link)
        #             news_author=subbrowser.find_elements_by_xpath('//meta[@name="author"]')
        #             if len(news_author)>0:
        #                 news_author=news_author[0].get_attribute('textContent')
        #             news_keywords=subbrowser.find_elements_by_xpath('//meta[@name="keywords"]')
        #             if len(news_keywords)>0:
        #                 news_tags_list.append(news_keywords[0].get_attribute('textContent').split(','))
        #             news_updated_src=subbrowser.find_elements_by_xpath('//meta[@http-equiv="last-modified"]')
        #             if len(news_updated_src)>0:
        #                 news_updated=news_updated_src[0].get_attribute('textContent')
        #
        #         except WebDriverException, e:
        #             self.logger.debug(e)
        #         curr_news={
        #          "author": news_author,
        #          "id": news_id,
        #          "link": news_link,
        #          "source": news_source,
        #          "summary": news_summary,
        #          "tags": news_tags_list,
        #          "title": news_title
        #          #"updated": news_updated,
        #          #"raw":news_raw
        #         }
        #         self.update([curr_news])
        #         #news.append(curr_news)
        #     #self.logger.debug("Batch news:"+str(len(news)))
        #     #self.update(news)
        #     news=[]
        #     try:
        #         next_page=browser.find_elements_by_xpath('//a[contains(text(),"next") and contains(@href,"?page=")]')
        #         if len(next_page)>0:
        #             next_page[0].click()
        #         else:
        #             self.logger.debug("no more page to crawl")
        #             break
        #     except NoSuchElementException:
        #         self.logger.debug("no more page to crawl")
        #         break
        # subbrowser.close()
        # subbrowser.quit()
        return False

    def dolphin_get(self):
        """ not implemented yet """
        return False

    #@profile
    def do_predict(self,doc):
        """ call deepdetect web service to predict topics """
        results=Results(self.logger,1,str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
        try:
            parameters_input = {}
            parameters_mllib = {}
            parameters_output = {}

            data=""
            dd_info=self.dd.info()
            if 'title' in doc:
                data=data+doc['title']+"\r\n"
            if 'summary' in doc:
                data=data+doc['summary']+"\r\n"
            if 'text' in doc:
                data=data+doc['text']+"\r\n"
            if "tags" in doc and type(doc["tags"])==list:
                data+",".join(doc['tags'])
            self.logger.debug("Predict: "+doc['link'])
            doc['topics']=[]
            data=self.url_validator.sub(' ',data)
            data = re.sub(r'^https?:\/\/.*[\r\n]*', '', data, flags=re.MULTILINE)
            data = re.sub(r"http\S+", "", data,re.MULTILINE)
            for mod in dd_info['head']['services']:
                self.logger.debug("Predict: "+mod['name'])
                self.logger.debug('Predict: dd.post_predict('+mod['name']+',[data],parameters_input,parameters_mllib,parameters_output)')
                classif = self.dd.post_predict(mod['name'],[data],parameters_input,parameters_mllib,parameters_output)
                self.logger.debug("Predict: "+json.dumps(classif))
                if classif['status']['code']==200:
                    if type(classif['body']['predictions']) is list:
                        for prediction in classif['body']['predictions']:
                            for classe in prediction['classes']:
                                doc['topics'].append({"score":classe['prob']*100,"label":classe['cat']})
                        results.add_success({'url':doc['link'],'message':doc['topics']})
                    else:
                        doc['topics'].append({"score":classif['body']['predictions']['classes']['prob']*100,"label":classif['body']['predictions']['classes']['cat']})
                        results.add_success({'url':doc['link'],'message':doc['topics']})
                else:
                    results.add_fail({'url':doc['link'],'message':"Predict: DD failed result code:"+str(classif['status']['code'])})
        except Exception as e:
            results.add_error({'url':doc['link'],'lib':"dede",'message':str(e)})

        if len(doc['topics'])<1:
            doc.pop('topics')
        return [doc,results.results]

    def update(self,entries):
        """ create or update news in the storage """
        return self.storage.bulk(entries)

        # for doc in entries:
        #     if "html" in doc:
        #         self.logger.debug("HTML Size:"+str(len(doc['html'])))
        #     self.logger.debug("URI Exclusion test on:"+doc['link'])
        #     self.logger.debug(not any(re.match(regex, doc['link']) for regex in self.uri_exclusion))
        #     if self.url_validator.match(doc['link'])!=None:
        #         if not "source_type" in doc:
        #             doc["source_type"]="rss"
        #         self.logger.debug("Store:"+doc['link'])
        #         if "origin" in doc:
        #             self.storage.put(type="doc",source=doc["origin"],data=doc)
        #         else:
        #             self.storage.put(type="doc",source=self.id,data=doc)
        #     else:
        #         self.logger.debug("Storage rejected pattern mismatch or uri excluded in global settings for:"+doc['link'])

    def text_to_string(self,text):
        return self.storage.text_to_string(text)

    #@profile
    def get_source(self,url,nb_try=10):
        """ Attempt to navigate throw multiple redirect of web pages to find real news

        :param: str url url to scrap and extract content_crawl
        :return: json extracted attributes mostly text, tags, summary and title if extraction success
        """
        results=Results(self.logger,1,str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))

        url_exclusion=any(re.match(regex, url) for regex in self.uri_exclusion)
        extension_exclusion=any(re.match(regex, url) for regex in self.file_extensions_exclusion)

        if url_exclusion:
            results.add_fail({"url":url,"message":"url has been excluded by settings EXCLUDED_URIS"})
            doc={"link":url,"content":[{"base":url,"language":""}]}
            return [doc, results.results]

        if extension_exclusion:
            results.add_fail({"url":url,"message":"url has been excluded by settings EXCLUDED_FILE_EXTENSIONS"})
            doc={"link":url,"content":[{"base":url,"language":""}]}
            return [doc, results.results]

        res = self.http.request('GET', url, preload_content=False)
        doc_type = res.info().maintype()
        type_exclusion=any(re.match(regex, doc_type) for regex in self.file_extensions_exclusion)

        if type_exclusion:
            results.add_fail({"url":url,"message":"document type has been excluded by settings EXCLUDED_FILE_EXTENSIONS"})
            doc={"link":url,"content":[{"base":url,"language":""}]}
            return [doc, results.results]

        html=""
        text=""
        title=""
        summary=""
        tags=[]

        #manage not web documents
        if doc_type != "html" and doc_type != "text" and doc_type != "htm" and doc_type != "application":
            #create temporary file to download the document
            tmp_file = tempfile.TemporaryFile()
            last_lib="magic"
            with open(tmp_file, 'wb') as out:
                out.write(res.data)
                mimes = magic.mime.from_file(out) # Get mime type
                ext = magic.mimetypes.guess_all_extensions(mimes)[0] # Guess extension
                last_lib="textract"
                #extract text from the document
                text = textract.process(out, extension=ext)
        #if pure text just download it
        elif doc_type == "text":
            text=res.data
            last_lib="No Lib"


        #most effective library to crawl newscontent found
        if len(text)<self.config['NEWS_MIN_TEXT_SIZE']:
            #try newspaper content scraping
            last_lib="newspaper"

            try:
                self.logger.debug("Source: try to extract content with newspaper "+url)
                article = Article(url)
                article.download()
                article.parse()
                html=article.html
                article.nlp()
                text=article.text
                summary=article.summary
                title=article.title
                tags=article.keywords
                url=article.url
		if len(text) == 0:
                    results.add_error({'url':url,'lib':last_lib,'message':'Could not extract any text'})
                else:
                    results.add_success({'url':url,'lib':last_lib,'message':'news extraction','title':title,'tags':tags,'text_size':len(text)})
                del article
            except Exception as e:
                results.add_error({'url':url,'lib':last_lib,'message':str(e)})

        # flood the source and make dfm a blocked origin use phantomjs instead
        # if not self.config['FAST_CRAWLING_MODE']:
        #     try:
        #         self.logger.debug("Source: trying html downlaod with urllib3:"+url)
        #         url=self.redirects_pass_through(url)
        #     except MaxRetryError as e:
        #         self.logger.debug("Source: max retry error on redirect pass through:"+url)
        #         pass

        if not self.config['FAST_CRAWLING_MODE']:
            try:
                if len(text)<self.config['NEWS_MIN_TEXT_SIZE']:
                    self.logger.debug("Source: trying content extraction:"+url)
                    last_lib="urllib3"
                    resp = self.http.request('GET', url)
                    html=resp.data
                    text=resp.text
                    del resp
                    self.logger("Source: "+last_lib+" html size="+str(len(html)))

                    #attempt readability text extraction
                    last_lib="bs4"
                    bs = BeautifulSoup(html,"lxml")

                    if bs.body:
                        data = bs.body.findAll(text=True)
                        text="\r\n".join(filter(self._visible, data))
                        results.add_success({'url':url,'lib':last_lib,'message':'body text extraction','text_size':len(text)})

                    tags=list(bs.keywords)
                    if len(tags)==0:
                        ctags = bs.findAll(attrs={"name":"keywords"})
                        if len(ctags)>0:
                            tags=ctags[0]['content'].encode('utf-8').split(',')
                            results.add_success({'url':url,'lib':last_lib,'message':'tags extraction','tags':tags})
                    else:
                        results.add_success({'url':url,'lib':last_lib,'message':'tags extraction','tags':tags})

                    title=bs.title.string

                    del bs


                    if len(text)<self.config['NEWS_MIN_TEXT_SIZE']:
                        try:
                            last_lib="readability"
                            r_doc=Document(text)
                            r_text=r_doc.summary()
                            if len(title)<3:
                                title=r_doc.title()
                                results.add_success({'url':url,'lib':last_lib,'message':'title extraction','title':title})

                            bs2 = BeautifulSoup(r_text,"lxml")
                            if bs2.body:
                                data = bs2.body.findAll(text=True)
                                text="\r\n".join(filter(self._visible, data))
                                results.add_success({'url':url,'lib':last_lib,'message':'body text extraction','text_size':len(text)})
                            del bs2

                            if len(tags)==0:
                                ctags = bs2.findAll(attrs={"name":"keywords"})
                                if len(ctags)>0:
                                    tags=ctags[0]['content'].encode('utf-8').split(',')
                                    results.add_success({'url':url,'lib':last_lib,'message':'tags extraction','tags':tags})
                            del bs2
                        except Exception as e:
                            results.add_error({'url':url,'lib':last_lib,'message':str(e)})
            except Exception as e:
                results.add_error({'url':url,'lib':last_lib,'message':str(e)})

        try:
            lang_detect=detect(text)
        except Exception as e:
            results.add_error({'url':url,'lib':last_lib,'message':str(e)})
            lang_detect=""

        doc={"link":url,"content":[{"base":url,"language":lang_detect}]}
        if len(title)>0:
            doc["title"]=title
        if self.config['STORE_HTML'] and len(html)>0:
            doc["html"]=base64.b64encode(self.text_to_string(html))
        if len(summary)>0:
            doc["summary"]=summary
        if len(text)>0:
            doc["text"]=text
        if len(tags):
            doc["tags"]=tags


        if len(text)<self.config['NEWS_MIN_TEXT_SIZE'] and not self.config['FAST_CRAWLING_MODE']:
            last_lib="phantomjs"
            doc=self.get_dynamic_source(url,html,text,title,tags)
            if 'text' in doc:
                results.add_success({'url':doc['link'],'lib':last_lib,'message':'news extraction success','text_size':len(doc['text'])})
            else:
                results.add_success({'url':doc['link'],'lib':last_lib,'message':'news extraction failed'})

        results.add_success({'url':doc['link'],'lib':last_lib,'message':'news extraction complete'})
        results.finish()
        return [doc, results.results]
        # result={"text":"", "link":url}
        # status=404
        # target_url=url
        # title=""
        # html=""
        # text=""
        # target_url=self.unshorten_url(url)
        # article=None
        # try:
        #     self.logger.debug("Source :Extract content with newspaper")
        #     article = Article(target_url)
        #     article.download()
        #     article.parse()
        # except:
            # Newspaper bug: CRITICAL:jpeg error with PIL, cannot concatenate 'str' and 'NoneType' objects
            # Issue https://github.com/codelucas/newspaper/issues/95
            # 2015 Fix https://github.com/codelucas/newspaper/pull/154/commits/d108a313c6206a1d1516a01f4f64a031da29b0f0
            # 2015 error print https://github.com/codelucas/newspaper/pull/154/commits/4ab4334a9b754c82eabbb9ca0f45b00873b1c43a
            # End of Python 2 support December 2014 https://github.com/codelucas/newspaper/releases/tag/0.0.9
            # The only way to get Newspaper fix is to switch to python 3
        #     self.logger.debug("Source: Web Page parts extraction: Newspaper lib failed, extract with BeautifulSoup")
        #     try:
        #         response, content = self.http.request('GET',target_url)
        #         while meta_redirect(content):
        #             self.logger.debug("Source: attempt to pass redirects with BeautifulSoup")
        #             response, content = self.http.request(self.meta_redirect(content),"GET")
        #
        #
        #         status=response.status
        #         if response.get_redirect_location():
        #             target_url=get_redirect_location()
        #         else:
        #             target_url=url
        #         html=content
        #         result=self.extract_page_elements(target_url,html)
        #
        #
        #         response.release_conn()
        #         del response
        #     except:
        #         self.logger.debug("Source: BeautifulSoup  and requests failed")
        #
        # if article is not None:
        #     text=self.html_to_text(article.html)
        #     title=article.title
        #     tags=article.keywords
        #     target_url=article.url
        #     html=article.html
        #     try:
        #         lang_detect=detect(text)
        #     except:
        #         self.logger.debug("No Lang found")
        #         lang_detect=""
        #     result={"title":title,"link":target_url,"html":base64.b64encode(html.encode('utf_8', 'xmlcharrefreplace')),"text":text,"tags":tags,"content":[{"base":url,"language":lang_detect}]}
        #     del article
        #
        # if len(result['text'])>self.min_text_size:
        #     self.logger.debug("Source: gotten"+target_url+ " tags:"+str(len(tags)))
        #     return result
        # else:
        #     self.logger.debug("Source: Too Small Page, try Dynamic Source "+url+" \r\n"+text)
        #     #return {"link":url}
        #     try:
        #         result=self.get_real_dynamic_source(target_url,html)
        #         if 'text' in result:
        #             if len(result['text'])>self.min_text_size:
        #                 self.logger.debug("Dynamic Source: gotten"+result['link']+" \r\n"+result['text'])
        #                 return result
        #             else:
        #                 self.logger.debug("Source: Too Small Page "+result['link']+" \r\n"+result['text'])
        #                 return {"link":url}
        #         else:
        #             self.logger.debug("Source: Empty Page "+result['link'])
        #             return {"link":url}
        #     except:
        #         self.logger.debug("Dynamic Source: Failed to proecess "+result['link'])
        #         return {"link":url}

    def get_dynamic_source(self,url,html=None,text="",title="",tags=[],nb_try=10):
        self.logger.debug("Dynamic Source: PhantomJS: "+url)
        try:
            curr_html=self.browser.page_source
            self.browser.get(url)
            src_try=0
            while curr_html==self.browser.page_source and src_try<nb_try:
                self.logger.debug("Dynamic Source: PhantomJS Loop... url:"+url)
                src_try+=1
            self.logger.debug("Dynamic Source: PhantomJS extracting content... url:"+url)
            html=self.browser.page_source
            r_text=Document(html).summary()
            r_bs = BeautifulSoup(r_text,"lxml")
            if r_bs.body:
                data = r_bs.body.findAll(text=True)
                text="\r\n".join(filter(self._visible, data))
            else:
                text=""
            del r_bs

            if len(text)<self.min_text_size:
                self.logger.debug("Dynamic Source: content too poor, PhantomJS Wait 35sec ... url:"+url)
                time.sleep(40)
                html=self.browser.page_source
                r_text=Document(html).summary()
                r_bs = BeautifulSoup(r_text,"lxml")
                if r_bs.body:
                    data = r_bs.body.findAll(text=True)
                    text="\r\n".join(filter(self._visible, data))
                else:
                    text=""
                del r_bs

            if len(text)>0:
                bs = BeautifulSoup(html,"lxml")
                self.logger.debug("Dynamic Source: extract title and tags url:"+url)
                ctitle=bs.findAll(attrs={"name":"title"})
                if len(ctitle)>0:
                    title=ctitle[0]['content'].encode('utf-8')

                if len(tags)==0:
                    ctags = bs.findAll(attrs={"name":"keywords"})
                    if len(ctags)>0:
                        tags=ctags[0]['content'].encode('utf-8').split(',')
                del bs

            try:
                self.logger.debug("Dynamic Source: detect lang:"+url)
                lang_detect=detect(text)
            except:
                self.logger.debug("Dynamic Source: lang detection failed:"+url)
                lang_detect=""

            result={"title":title,"link":url,"html":base64.b64encode(self.text_to_string(html)),"text":text,"tags":tags,"content":[{"base":url,"language":lang_detect}]}
            self.logger.debug("Dynamic Source: content extraction with Selenium PhantomJS lib: "+result['link']+" "+result['title']+" "+",".join(result['tags']))
            return result
        except (WebDriverException, HTTPException, URLError) as e:
            self.logger.debug("Dynamic Source: PhantomJS error url:"+url)
            #self.logger.debug("Next Chromium: "+url)
            return {"link":url}
            #return self.get_real_dynamic_source(url)
    #
    # def get_dom(self,html):
    #     """ return dom object from html string
    #     :param str html: html raw source in a string
    #     :returns: lxml dom object
    #     """
    #     return lxml.html.document_fromstring(html)
    #
    #@profile
    def _visible(self,element):
        #catch only visible elements in the web page source code
        if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
            return False
        elif re.match('<!--.*-->', str(element.encode('utf-8'))):
            return False
        return True

    # def extract_page_elements(self,target_url,html):
    #     # try:
    #     self.logger.debug("HTML SIZE FOR EXTRACTION:"+str(len(html)))
    #     title=""
    #     text=""
    #     tags=""
    #     html_b64=""
    #     text=self.html_to_text(html)
    #     self.logger.debug(text)
    #     bsoup_parsed = BeautifulSoup(html)
    #     if text is None:
    #         text =[''.join(s.findAll(text=True))for s in soup.findAll('p')]
    #
    #     try:
    #         title=bsoup_parsed.title.text
    #         tags=bsoup_parsed.findAll(attrs={"name":"keywords"})[0]['content'].encode('utf-8').split(',')
    #     except:
    #         self.logger.debug("No Tags in the news:"+target_url)
    #         tags=[]
    #         pass
    #     if isinstance(html, str):
    #         self.logger.debug("ordinary string")
    #         html_b64=base64.b64encode(html)
    #     elif isinstance(html, unicode):
    #         self.logger.debug("unicode string")
    #         try:
    #             html_b64=base64.b64encode(html.encode('utf_8', 'xmlcharrefreplace'))
    #             self.logger.debug("ascii xmlreplace")
    #         except:
    #             try:
    #                 html_b64=base64.b64encode(html.encode('utf_8', 'replace'))
    #                 self.logger.debug("ascii replace")
    #             except:
    #                 try:
    #                     html_b64=base64.b64encode(html.encode('utf_8', 'ignore'))
    #                     self.logger.debug("ascii ignore")
    #                 except:
    #                     html_b64=base64.b64encode(html.decode().encode('utf_8', 'xmlcharrefreplace'))
    #                     self.logger.debug("decode ascii xmlreplace")
    #     else:
    #         self.logger.debug("not a string")
    #
    #
    #     try:
    #         lang_detect=detect(text)
    #     except:
    #         lang_detect=""
    #     self.logger.debug("TEXT SIZE FOR EXTRACTION:"+str(len(text)))
    #     return {"title":title,"link":target_url,"html":html_b64,"text":text,"tags":tags,"content":[{"base":target_url,"language":lang_detect}]}
        # except:
        #     self.logger.debug("Extract elements: failed text extraction for html")
        #     return {"title":"","link":target_url,"html":"","text":"","tags":"","content":[{"base":"","language":""}]}


    # @profile
    # def html_to_text(self,html):
    #     """ extract main text from an html page
    #     :param str html: raw html code as string
    #     :returns: main text of the web page
    #     """
    #     if html:
    #         try:
    #             pseudo_html=Document(html).summary()
    #         except:
    #             self.logger.debug("Text body: READABILITY TEXT EXTRACTION FAILED")
    #             pseudo_html=html
    #         try:
    #             soup = BeautifulSoup(pseudo_html,"lxml")
    #             if soup.body:
    #                 data = soup.body.findAll(text=True)
    #                 text="\r\n".join(filter(self._visible, data))
    #             else:
    #                 self.logger.debug("Text body: BEAUTIFULSOUP NO BODY DETECTED")
    #                 return "No Text Extracted"
    #         except:
    #             self.logger.debug("Text body: BEAUTIFULSOUP TEXT EXTRACTION FAILED")
    #             return "No Text Extracted"
    #     self.logger.debug("Text body: TEXT EXTRACTION FAILED GLOBALY")
    #     return "No Text Extracted"
    #
    # def get_real_dynamic_source(self,url,curr_html,nb_try=10):
    #     self.logger.debug("Dynamic content: browsing...")
    #     result=self.extract_page_elements(url,curr_html)
    #
    #     try:
    #         with wait_for_page_load(self.browser):
    #             self.logger.debug("Dynamic content: waiting target page...")
    #             self.browser.get(url)
    #             html=self.browser.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
    #             if curr_html!=html:
    #                 self.logger.debug("Dynamic content: Target page found!")
    #                 return self.extract_page_elements(self.browser.current_url,html)
    #             time.sleep(3)
    #     except:
    #         self.logger.debug("Dynamic content: waiting class failed")
    #         pass
    #
    #     try:
    #         src_try=0
    #         html=self.browser.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
    #         while curr_html==html and src_try<nb_try:
    #             self.logger.debug("Dynamic content: Browser Loop...")
    #             src_try+=1
    #         html=self.browser.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
    #         result=self.extract_page_elements(self.browser.current_url,html)
    #     except:
    #         self.logger.debug("Dynamic content: looping failed")
    #         pass
    #
    #     try:
    #         if len(resul['text'])<self.min_text_size:
    #             self.logger.debug("Dynamic content: Browser Wait 35sec ...")
    #             time.sleep(60)
    #         result=self.extract_page_elements(self.browser.current_url,self.browser.page_source)
    #     except:
    #         self.logger.debug("Dynamic content: waiting 60sec failed")
    #         pass
    #
    #     if len(result['text'])>self.min_text_size:
    #         self.logger.debug("Dynamic content: Browser found page:"+self.browser.current_url)
    #         html=self.browser.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
    #         return self.extract_page_elements(self.browser.current_url,html)
    #     else:
    #         try:
    #             self.logger.debug("Dynamic content: Not found page:"+url)
    #             return {"link":url}
    #         except WebDriverException as e:
    #             self.logger.debug("Dynamic content:\n"+e.__str__())
                # return {"link":url}

    def meta_redirect(self,content):
        """ meta management of url redirection pages for requests """
        soup  = BeautifulSoup.BeautifulSoup(content)

        result=soup.find("meta",attrs={"http-equiv":"Refresh"})
        if result:
            wait,text=result["content"].split(";")
            if text.strip().lower().startswith("url="):
                url=text[4:]
                return url
        return None

    #@profile
    def redirects_pass_through(self,url,retries=3):
        #test infinite loop from https://kev.inburke.com/kevin/urllib3-retries/
        while True:
            try:
                self.logger.debug("Redirects: url for redirects pass through:"+url)
                resp = self.http.request('GET', url)
                self.logger.debug("Redirects: status: "+str(resp.status)+" url: "+url)
                if resp.status < 300:
                    self.logger.debug("Redirects: found target:"+url)
                    return url
                if resp.status in [429]:
                    self.logger.debug("Redirects: Too many requests on the server, dfm is blocked, waiting for server new acceptance"+url)
                    retries+=1
                    if retries>self.config['CRAWLING_RETRIES']:
                        self.logger.debug("Redirects: Too many requests on the server, exceed CRAWLING_RETRIES, abort crawling:"+url)
                        return url
                    retries -= 1
                    if retries <= 0:
                        raise
                    time.sleep(2 ** (3 - retries))
                    continue
                if resp.status in range(400,428):
                    self.logger.debug("Redirects: Server refused to answer, abort crawling:"+url)
                    return url
                if resp.status >= 500:
                    self.logger.debug("Redirects: Server error:"+url)
                    return url
                    # retries -= 1
                    # if retries <= 0:
                    #     raise
                    # time.sleep(2 ** (3 - retries))
                    # continue
            except MaxRetryError as e:
                self.logger.debug("Redirects: Max retry error:"+url)
                return url
            except (ConnectionError, ConnectTimeoutError):
                self.logger.debug("Redirects: Connection timeout error:"+url)
                retries -= 1
                if retries <= 0:
                    raise
                time.sleep(2 ** (3 - retries))
            except TimeoutError:
                self.logger.debug("Redirects: Timeout error:"+url)
                retries -= 1
                if retries <= 0:
                    raise
                time.sleep(2 ** (3 - retries))
                continue


        # #try to pass redirects with requests
        # self.logger.debug("Redirects: depth:"+str(depth)+" entering in redirect pass function url:"+url)
        # headers={"user-agent":self.config['CRAWLING_USERAGENT']}
        # response, content = self.http.request('GET',url)
        #
        # if int(status/100) == 3 and response.getheader('Location'):
        #     return self.redirects_pass_through(response.getheader('Location'),depth=depth+1)
        # elif meta_redirect(content):
        #     while meta_redirect(content):
        #         self.logger.debug("Redirects: depth:"+str(depth)+" attempt to pass redirects with BeautifulSoup:"+response.url)
        #         response, content = self.http.request(self.meta_redirect(content),"GET")
        #     self.logger.debug("Redirects: depth:"+str(depth)+" exit from BS4 loop, return to recursive steps:"+response.url)
        #     return self.redirects_pass_through(response.url,depth=depth+1)
        # else:
        #     self.logger.debug("Redirects: depth:"+str(depth)+" no more redirect found returning url"+response.url)
        #     return response.url




        #try to pass redirects with urllib3

        # if response.get_redirect_location():
        #     url=get_redirect_location()
        # else:
        #     target_url=url
    #     "Attempt to unshorten url to get real news origin"
    #     if(depth<3):
    #         try:
    #             parsed = urlparse.urlparse(url)
    #             h = httplib.HTTPConnection(parsed.netloc)
    #             resource = parsed.path
    #             if parsed.query != "":
    #                 resource += "?" + parsed.query
    #             h.request('HEAD', resource )
    #             response = h.getresponse()
    #             if response.status/100 == 3 and response.getheader('Location'):
    #                 depth+=1
    #                 return self.unshorten_url(response.getheader('Location'),depth=depth) # changed to process chains of short urls
    #             else:
    #                 return url
    #         except:
    #             return url
    #     else:
    #         return url

    #@profile
    def get_content(self,doc):
        """ get content of a news collected from a feed (news source) """
        results=Results(self.logger,1,str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
        if self.url_validator.match(doc['_source']['link']):
            doc_result=self.get_source(doc['_source']['link'])
            results.add_success(doc_result[1])
            content={"doc":doc_result[0]}
            #check potential collected tags
            if "tags" in content["doc"]:
                if type(content["doc"]["tags"]) == list and len(content["doc"]["tags"])>0:
                    if "tags" in doc["_source"]:
                        #merge list of tags and remove duplicates
                        in_first = set(doc["_source"]["tags"])
                        in_second = set(content["doc"]["tags"])
                        in_second_but_not_in_first = in_second - in_first
                        content["doc"]["tags"] = doc["_source"]["tags"] + list(in_second_but_not_in_first)
                        self.logger.debug("Content: Tags total included"+str(len(content["doc"]["tags"])))
                        results.add_success({'url':doc["_source"]["link"],'message':'tags list joint','tags':doc["_source"]["tags"]})
                        del in_first, in_second, in_second_but_not_in_first
                else:
                    content["doc"].pop("tags")
                    results.add_fail({'url':doc["_source"]["link"],'message':'no tags in news'})

            if "text" in content['doc'] and len(content['doc']['text'])>self.min_text_size:
                doc['_source'].update(content['doc'])
                results.add_success({'url':doc["_source"]["link"],'message':'body text detected','text_size':len(doc['_source']['text'])})

            else:
                if "text" in content['doc']:
                    text=content['doc']['text']
                    doc['_source'].update(content['doc'])
                    result=self.storage.delete(item_id=doc['_id'])
                    results.add_fail({'url':doc["_source"]["link"],'message':'body text too small','text_size':len(doc['_source']['text']),"text":doc['_source']['text'],"deletion":result})
                    del doc
                    doc=None
                else:
                    text=""
                    result=self.storage.delete(item_id=doc['_id'])
                    results.add_fail({'url':doc["_source"]["link"],'message':'no body text detect',"deletion":result})
                    del doc
                    doc=None

        else:
            results.add_fail({'url':doc["_source"]["link"],'message':'url pattern mismatch'})
            del doc
            doc=None
        results.finish()
        return [doc, results.results]
