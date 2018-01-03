#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"Data Feed Manager Machine Learning model trainer"

from memory_profiler import profile
import sys, os, time, argparse
from dd_client import DD


class ModelTrainer:
    """ Prediction Model trainer class
        binary char-based model training class
    """
    def __init__(self,structure,logger,config):
        """ Instanciate a model trainer
        :param dic structure: Model Trainer specific settings
            eg: {"model-repo":"../models/mymodel","training-repo":"../training/mytraining","sname":"MyTrainer","test_split":0.01,"base-lr":0.01,"clevel":False,"sequence":140,"iterations":50000,"test_interval":1000,"stepsize":15000,"destroy":True,"resume":False,"finetune":False,"weights":"","nclasses":2,"documents":True,"batch-size":128,"test-batch-size":16,"gpuid":0,"mllib":"xgboost","lregression":False}
            *model-repo* location of the model
            *training-repo* location of the training files
            *sname* service name
            *test_plit* training split between 0 and < 1,type=float,default=0.01
            *base_lr* initial learning rate,default=0.01,type=float
            *clevel* character-level convolutional net,type=boolean
            *sequence* sequence length for character level models,default=140,type=int
            *iterations* number of iterations,default=50000,type=int
            *test_interval* test interval',default=1000,type=int
            *stepsize* lr policy stepsize',default=15000,type=int
            *destroy* whether to destroy model',type=boolean
            *resume* whether to resume training,type=boolean
            *finetune* whether to finetune,type=boolean
            *weights* pre-trained weight file, when finetuning
            *nclasses* number of classes,type=int,default=2
            *documents* whether to train from text documents (as opposed to sentences in one doc),type=boolean
            *batch_size* batch size,type=int,default=128
            *test_batch_size* test batch size,type=int,default=16
            *gpu* enable gpu usage is True, default=False
            *gpuid* specify gpu id,type=int,default=0
            *mllib* caffe or xgboost,default='caffe'
            *lregression* whether to use logistic regression,type=boolean
        :param obj logger: DFM logger object
        :param obj storage: DFM storage object
        :param obj config: DFM global config object
        :returns: ModelTrainer object (instance of a modeltrainer class)
        """
        self.config=config
        self.structure=structure
        self.logger=logger
        self.nclasses = self.structure['nclasses']
        self.description = 'classifier'
        self.sname=self.structure['sname']
        self.mllib = self.structure['mllib']
        self.dd = DD(config['DEEP_DETECT_URI'])
        self.dd.set_return_format(self.dd.RETURN_PYTHON)

    def createMLTrainerService(self):
        """ Create ML Trainer service in DeepDetect """
        if self.structure['lregression']:
            self.template = 'lregression'
        else:
            self.template = 'mlp'
            layers = [800,500,200]
        if self.structure['clevel']:
            self.template = 'convnet'
            self.layers = ['1CR256','1CR256','4CR256','1024','1024']
        self.model = {'templates':'../templates/caffe/','repository':self.structure['model-repo']}
        self.parameters_input = {'connector':'txt','sentences':False,'characters':self.structure['clevel'],'read_forward':True}
        if self.structure['documents']:
            self.parameters_input['sentences'] = False
        if self.structure['clevel']:
            self.parameters_input['sequence'] = self.sequence
            #parameters_input['alphabet'] = 'abcdef0123456789'  # hex
        #    parameters_input['alphabet'] = '_-,:?/.(){}*%0123456789abcdefghijklmnopqrstuvwxyz' # opcode
            #parameters_input['alphabet'] = "abcdefghijklmnopqrstuvwxyz0123456789,;.!?'"#\"/\\|_@#$%^&*~`+-=<>"
        self.parameters_mllib = {'template':self.template,'nclasses':self.nclasses,'db':True,'dropout':0.5}
        if self.mllib == 'xgboost':
            self.parameters_mllib['db'] = False
        if not self.template == 'lregression':
            self.parameters_mllib['layers'] = layers
        #parameters_mllib = {'nclasses':nclasses,'db':True}
        if self.structure['finetune']:
            self.parameters_mllib['finetuning'] = True
            if not self.structure['weights']:
                logger.error('Finetuning requires weights file')  # server will fail on service creation anyways
            else:
                self.parameters_mllib['weights'] = self.structure['weights']
        self.parameters_output = {}
        self.logger.debug("dd.put_service("+str(self.structure['sname'])+","+str(self.model)+","+str(self.description)+","+str(self.mllib)+","+str(self.parameters_input)+","+str(self.parameters_mllib)+","+str(self.parameters_output)+")")
        return self.dd.put_service(self.structure['sname'],self.model,self.description,self.mllib,self.parameters_input,self.parameters_mllib,self.parameters_output)

    def trainModel(self):
        """ Train the model. """
        self.train_data = [self.structure['training-repo']]
        self.parameters_input = {'test_split':self.structure['test_plit'],'shuffle':True,'db':True}
        if not self.structure['clevel']:
            self.parameters_input['min_word_length'] = 5
            self.parameters_input['min_count'] = 10
            self.parameters_input['count'] = False
            if self.mllib == 'xgboost':
                self.parameters_input['tfidf'] =  True
                self.parameters_input['db'] = False
        else:
            self.parameters_input['sentences'] = True
            self.parameters_input['characters'] = True
            self.parameters_input['sequence'] = self.sequence
        if self.structure['documents']:
            self.parameters_input['sentences'] = False
        if self.mllib == 'caffe':
            self.parameters_input['db']=True
            self.parameters_mllib = {
             'gpu':self.structure['gpu'],
             'gpuid':self.structure['gpuid'],
             'resume':self.structure['resume'],
             'net':{
              'batch_size':self.structure['batch_size']
             },
             'solver':{
              'test_interval':self.structure['test_interval'],
              'test_initialization':False,
              'base_lr':self.structure['base_lr'],
              'solver_type':'ADAM',
              'iterations':self.structure['iterations']
             }
            }#,'lr_policy':'step','stepsize':self.structure['stepsize'],'gamma':0.5,'weight_decay':0.0001}}
        elif self.mllib == 'xgboost':
            self.parameters_mllib = {
              'iterations':self.structure['iterations'],
              'objective':'multi:softprob',
              'booster_params':{'max_depth':50}
             }
        self.parameters_output = {'measure':['mcll','f1','cmdiag','cmfull']}
        if self.nclasses == 2:
            self.parameters_output['measure'].append('auc')
        self.logger.debug("dd.post_train("+self.structure['sname']+","+str(self.train_data)+","+str(self.parameters_input)+","+str(self.parameters_mllib)+","+str(self.parameters_output)+",async="+str(True)+")")
        self.dd.post_train(self.structure['sname'],self.train_data,self.parameters_input,self.parameters_mllib,self.parameters_output,async=True)
        time.sleep(1)
        train_status = ''
        while True:
            train_status = self.dd.get_train(self.sname,job=1,timeout=10)
            if train_status['head']['status'] == 'running':
                self.logger.debug(train_status['body']['measure'])
            else:
                self.logger.debug(train_status)
                break
        return train_status

    def clearMLTrainerService(self,clear=''):
        """ delete the service, keeping the model

        :param str clear: use clear='lib' to clear the model as well, default empty.
        :returns: DeepDetect delete result
        """
        return self.dd.delete_service(self.sname,clear=clear)
