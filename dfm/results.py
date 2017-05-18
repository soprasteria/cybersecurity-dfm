#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"Data Feed Manager Results Objects"
import time
import inspect
import json
from serializer import CustomSerializer

class Results:
     """ ElasticSearch results management
     results object must be instantiate at the beginning of the processing
     finish must be called at the end of the processing

     :param: int total total elements to process can be given when result object is instantiated
     :param: Logger logger application logger
     """
     def __init__(self,logger,total=None,current=None):
         self.start_time = time.time()

         if type(inspect.stack()) == list:
             if type(inspect.stack()) == list:
                 self.caller=str(inspect.stack()[1][1])+"."+str(inspect.stack()[1][3])
             else:
                 self.caller=str(None)
         else:
             self.caller=str(None)
         self.current=str(current)
         self.logger=logger
         self.serializer=CustomSerializer(logger)
         self.results={'call':self.caller,'function':self.current,"total":total,"count":0,"successful":0,"failed":0,'duration':0,'errors':0,'errors_list':[],'results':[]}
         self.logger.debug(self.current+' begin start_time:'+str(self.start_time)+" size:"+str(self.results['total']))

     def add_success(self,result=None):
         """ Add a success to the results

         :param result result object mostly json or string could be an instance from Results
         """
         self.results['successful']+=1
         self.results['count']+=1
         self.results['duration']=(time.time()-self.start_time)
         if result!=None:
             self.results['results'].append(result)
         self.logger.debug(self.current+' success: '+str(result))

     def add_fail(self,result=None):
         """ Add a fail to the results

         :param: result result object mostly json or string could be an instance from Results
         """
         self.results['failed']+=1
         self.results['count']+=1
         self.results['duration']=(time.time()-self.start_time)
         if result!=None:
             self.results['results'].append(result)
         self.logger.debug(self.current+' fail: '+str(result))

     def add_error(self,result=None):
         """ Add an error to the results

         :param: error error object mostly json or string could be an instance from Results or even an Exception object
         """
         self.results['errors']+=1
         self.results['count']+=1
         self.results['duration']=(time.time()-self.start_time)
         if result!=None:
             self.results['errors_list'].append(result)
         self.logger.error(self.current+' error: '+str(result))

     def set_total(self,total):
         """set total of elements to process

         :param: int total number of elements to process
         """
         self.results['total']=total
         self.logger.debug(self.current+' total: '+str(self.results['total']))

     def start(self):
         """ will reset with now time the start time which is by default at Result object instantiation time
         """
         self.start_time
         self.logger.debug(self.current+' start time: '+str(self.start_time))

     def finish(self):
         """ will set de duration which is updated at each call of an add function
         """
         self.results['duration']=(time.time()-self.start_time)
         self.logger.debug(self.current+' finish duration:'+str(self.results['duration'])+" size:"+str(self.results['total'])+" processed:"+str(self.results['count']))
