#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"Data Feed Manager Storage Management for ElasticSearch"

#from memory_profiler import profile
from datetime import datetime
import ssl
from elasticsearch import Elasticsearch, helpers, TransportError, ConnectionTimeout, ConnectionError, RequestError, RequestsHttpConnection, connection
import hashlib
import sys
import gc
import json
import inspect
from serializer import CustomSerializer
from results import Results
from flask import Flask
import urllib,urlparse
import time

class ProxiesConnection(RequestsHttpConnection):
     def __init__(self, *args, **kwargs):
         proxies = kwargs.pop('proxies', {})
         super(ProxiesConnection, self).__init__(*args, **kwargs)
         self.session.proxies = proxies


class Storage:
     """ ElasticSearch storage management """
     def __init__(self,logger=Flask(__name__).logger,config=Flask(__name__).config):
         """ create storage manager for ElasticSearch
         :params logger logger: flask logger object
         :params config config: DFM config object
         :returns: DFM storage object
         """
         self.config=config
         #ssl verify issue on latest version of python elasticsearch, workaround from here: https://github.com/elastic/elasticsearch-py/issues/712
         context = connection.create_ssl_context()
         context.check_hostname = False
         context.verify_mode = ssl.CERT_NONE
         if self.config['ES_PROXY'] is not None:
            self.es = Elasticsearch(self.config['ES_URIS'], timeout=self.config['ES_TIMEOUT'], connection_class=ProxiesConnection, proxies = self.config['ES_PROXY'],ssl_context=context)
         else:
            self.es=Elasticsearch(self.config['ES_URIS'],timeout=self.config['ES_TIMEOUT'],ssl_context=context)
         self.index=self.config['ES_INDEX']
         self.logger=logger
         self.serializer=CustomSerializer(logger)
         self.timeout=self.config['ES_TIMEOUT']
         self.limit=self.config['ES_BATCH_SIZE']

     def get(self,item_id,parent=None):
         """ get object from it's elasticsearch id
         :params string item_id: unique identifier string
         :returns: elasticsearch object
         """
         results=Results(self.logger,1,str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
         if parent is not None:
             result=self.es.get(index=self.index,doc_type='_all',routing=parent,id=item_id,ignore=[400,404])
             results.add_success({"id":result["_id"]})
         else:
             result=self.es.get(index=self.index,doc_type='_all',id=item_id,ignore=[400,404])
             results.add_success({"id":result["_id"]})
         results.finish()
         return [result,results.results]

     def bulk(self,doc_list):
        """ Simple elasticsearch bulk  wrapper

        :params doc doc_list of elasticsearch docs to update
        :returns: elasticsearch bulk result
        """
        results=Results(self.logger,len(doc_list),str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
        ready_doc_list=[]
        for doc in doc_list:
             if "origin" in doc:
                     doc['_routing']=doc['origin']
                     doc['_parent']=doc['origin']
             if "_index" not in doc:
                     doc['_index']=self.index
             if "_type" not in doc:
                     doc['_type']='doc'
             if "_id" not in doc:
                     if "link" in doc:
                         result_uuid=self.generate_uuid(doc)
                         doc['_id']=result_uuid[0]
                         results.add_success(result_uuid[0])
                     else:
                         result_uuid=self.generate_uuid(doc["doc"])
                         doc['_id']=result_uuid[0]
                         results.add_success(result_uuid[0])
             if "doc" in doc:
                     #json serialize date with special date parser otherwise ES index fail
                     doc["_source"]=json.loads(json.dumps(doc["doc"],default=self.serializer.to_json))
                     #remove source from doc
                     doc.pop("doc")

             ready_doc_list.append(doc)
        try:
            for result in helpers.parallel_bulk(self.es,ready_doc_list):
                if int(result[1]["index"]["status"])>=200 and int(result[1]["index"]["status"])<300:
                    results.add_success(result)
                else:
                    results.add_fail(result)
        except Exception as e:
            results.add_error(e)
        del ready_doc_list, doc_list
        results.finish()
        gc.collect()
        return results.results

     def update(self,data,item_id,dtype="doc",parent=None):
         """ Update existing object
         :params dic data: object data to update
         :params string item_id: id of object to update
         :params string dtype: object type **source** or **doc**
         :params string parent: parent unic identifier (mandatory for type doc, it's source id)
         :returns: elasticsearch updated object
         """
         results=Results(self.logger,1,str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
         #When you have a parent child relationship, you need to specify the parent in the URL each time you try to access it a child, since routing now depends on the parent.
         #json serialize with special date parser otherwise ES index fail
         result=self.es.update(index=self.index,doc_type=dtype,id=item_id,parent=parent,routing=parent,body=json.dumps(data,default=self.serializer.to_json),ignore=400)
         results.add_success(result["_id"])
         return results.results

     def delete(self, item_id, parent=None):
        """ delete object
        :params string item_id: unique identifier for the object
        :params string dtype: type of object **source** or **doc****source** or **doc**
        :params string parent: parent unique identifier (mandatory for type doc, it's source id)
        :return: results results object
        """
        results=Results(self.logger,1,str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
        to_delete_object=self.get(item_id)
        self.logger.debug("Storage: DELETE ITEM:"+item_id)
        if "_type" in to_delete_object:
            dtype=to_delete_object["_type"]
        else:
            to_delete_object=self.search("_id:"+item_id)[0]["hits"]["hits"][0]
            dtype=to_delete_object["_type"]
        if "_routing" in to_delete_object:
            result=self.es.delete(index=self.index,id=item_id,doc_type=dtype,routing=to_delete_object["_routing"],ignore=[400,404])
            results.add_success(result)

        else:
            result=self.es.delete(index=self.index,id=item_id,doc_type=dtype,ignore=[400,404])
            results.add_success(result)
        return results.results

     def text_to_string(self,text):
        if isinstance(text, str):
            self.logger.debug("ordinary string")
            return text
        elif isinstance(text, unicode):
            self.logger.debug("unicode string")
            try:
                self.logger.debug("utf-8 xmlreplace attempt")
                return text.encode('utf-8', 'xmlcharrefreplace')
            except:
                try:
                    self.logger.debug("utf-8 replace")
                    text.encode('utf-8', 'replace')
                except:
                        self.logger.debug("utf-8 ignore")
                        text.encode('utf-8', 'ignore')
        else:
            self.logger.debug("not a string")
            return text

     def generate_uuid(self,data):
         """ Generate UUID for any entry in ElasticSearch

         :param: dict data Item's data to insert in ES
         :result: item_id, results
         """
         results=Results(self.logger,1,str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
         #mandatory to instantiate md5 just before update otherwise different hash is generated
         hasher=hashlib.md5()
         #manage bug of hash generation for twitter and other api with query searches instead of standard uri
         if data['link'].find("//") > -1:
             obj_uri=urlparse.urlparse(self.text_to_string(data['link']))
             to_hash_uri=urllib.quote(obj_uri.scheme + "://" + obj_uri.netloc + obj_uri.path)

         else:
             #if uri not detected hash directly the query
             to_hash_uri=urllib.quote(self.text_to_string(data['link']))
         hasher.update(to_hash_uri)
         item_id=hasher.hexdigest()
         results.add_success({'url':data['link'],'uuid':item_id})
         return [item_id,results.results]


     def put(self,data,item_id=None,type="doc",source=None):
         """ add an object to storage
         "link" field inside "data" object is used to generate "Unique Idenfifier" for the object.
         This field is mandatory for all objects of any types put in the index.
         :params dic data: data for object creation
         :params string item_id: unique identifier for the object
         :params string type: type of object **source** or **doc****source** or **doc**
         :params string source: parent unique identifier (mandatory for type doc, it's source id)
         :returns: elasticsearch object
         """
         results=Results(self.logger,1,str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))

         if item_id is None:
             result_uuid=self.generate_uuid(data)
             item_id=result_uuid[0]
             results.add_success(result_uuid[1])

         try:
             if source is not None:
                    data['origin']=source
                    result=self.es.index(index=self.index,doc_type=type,id=item_id,parent=source,body=json.dumps(data,default=self.serializer.to_json),ignore=[400,404,409])
                    results.add_success(result["_id"])
             else:
                    result=self.es.index(index=self.index,doc_type=type,id=item_id,body=json.dumps(data,default=self.serializer.to_json),ignore=[400,404,409])
                    results.add_success(result["_id"])
         except (TransportError,ConnectionError, ConnectionTimeout,RequestError) as e:
             results.add_error(e)

         results.finish()
         return results.results

     def search(self,criteria):
         """ ElasticSearch simple search (only query lesser than 10000 results)
         :params string criteria: simple query criterias
         :returns: objects in elasticsearch result
         """
         results=Results(self.logger,current=str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))
         result=self.es.search(index=self.index,q=criteria,request_timeout=self.timeout)
         results.add_success(criteria)
         return [result,results.results]

     def query(self,criteria):
         """ Elasticsearch complex query (manage results over 10000 results)
         :params string criteria: complex query criterias
         :returns: objects in elasticsearch result
         """
         global_results=Results(self.logger,current=str(inspect.stack()[0][1])+"."+str(inspect.stack()[0][3]))

         limit=self.limit
         max_retry=10

         header_criteria=criteria.copy()
         header_criteria['size']=0
         results=self.es.search(index=self.index,body=header_criteria,request_timeout=self.timeout)

         if "size" in criteria:
             query_size=criteria["size"]
         else:
             query_size=results['hits']['total']

         global_results.set_total(query_size)

         #init loop variables
         results_status=0
         current_retry=0
         current_timeout=self.timeout
         timeout_exit=False

         #work around for nested it seems to not work properly with helpers
         # ES Error while using helpers.scan nested: SearchParseException[failed to parse search source
         # Issue opened https://github.com/elastic/elasticsearch-py/issues/466
         self.logger.debug("storage.query es.search:"+json.dumps(criteria))
         if query_size<limit or ("topics.score" in json.dumps(criteria)):
             results=self.es.search(index=self.index,body=criteria,request_timeout=self.timeout,size=query_size)
             global_results.set_total(1)
             global_results.add_success(criteria)
         else:
             self.logger.debug("storage.query helpers.scan:"+json.dumps(criteria))
             #org.elasticsearch.search.query.QueryPhaseExecutionException: Batch size is too large, size must be less than or equal to: [10000]. Scroll batch sizes cost as much memory as result windows so they are controlled by the [index.max_result_window] index level setting.
             results_gen=helpers.scan(self.es,query=criteria,scroll=self.config['ES_SEARCH_CACHING_DELAY'],preserve_order=True,request_timeout=self.timeout,size=1000,raise_on_error=False)
             global_results.add_success(criteria)

#             for result in results_gen:
             results['hits']['hits'].append(results_gen)
#                 global_results.add_success({'id':result['_id']})
#             del results_gen

#         gc.collect()
         return [results,global_results]
