# encoding: utf-8

import sys
import time

import ConfigParser
import datetime
import imp
import requests
import hashlib
import urlparse
import urllib,urllib3
import json
import feedparser

import os

import telepot
from telepot.namedtuple import InlineQueryResultArticle, InputTextMessageContent

dfm_api_base='http://localhost:12345/api/'
dfm_feed='http://localhost:12345/atom.xml?size=10'
telegram_dfm_id="/api/telegram"

http=urllib3.PoolManager(num_pools=3,timeout=urllib3.Timeout(connect=10, read=10),retries=urllib3.Retry(3, redirect=1))

config = ConfigParser.ConfigParser()
config.read('telegrambot.cfg')

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

def submitUrl(url,body,keywords=[]):
    source_uuid=generate_uuid({"link":telegram_dfm_id})
    news_uuid=generate_uuid({"link":url})
    doc= {}
    doc["origin"] = source_uuid
    doc["updated"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    doc["format"] = "telegram"
    if len(keywords)>0:
        doc["tags"] = keywords
    doc["summary"] = body["text"]
    message=body.pop('text')
    body['message']=message
    doc["content"] = body
    doc["source_type"] = "telegram"
    doc["link"] = url
    if "last_name" in body["from"]:
       last_name=body["from"]["last_name"]
    else:
       last_name=""
    doc["source"] = body['from']['first_name']+" "+last_name
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

def submitSource(link,stype,msg):
    doc= {}
    doc["title"]="Telegram "+msg['from']['first_name']+" "+stype+" source to scrap."
    doc["predict"]=True
    doc["enable_content"]=True
    doc["format"]=stype
    doc["depth"]="2"
    doc["summary"]=msg["text"]
    doc["step"]=1000
    doc["link"]=link
    doc["active"]=True
    doc["limit"]=200
    doc["freq"]=30


    creator=""
    if "first_name" in msg["from"]:
        creator=creator+msg["from"]["first_name"]+" "
    if "last_name" in msg["from"]:
        creator=creator+msg["from"]["last_name"]+" "
    if "id" in msg["from"]:
        creator=creator+str(msg["from"]["id"])+" "
    doc["creator"]=creator

    response = http.urlopen('PUT',dfm_api_base[:-1], headers={'content-type': 'application/json'},body=json.dumps(doc))
    print response.data
    response_dict=json.loads(response.data)
    if response_dict['failed']>0:
        code="Fail"
        result_msg=response_dict["error"]["reason"]
    else:
        code="success"
        for result in response_dict['results']:
            if '_id' in result:
                result_msg="Source ID for "+link+" is :"+result['_id']
    return "Your source add attempt is a "+code+" "+result_msg

def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)

    print(content_type, chat_type, chat_id, msg)

    if content_type == 'text':
        if "entities" in msg:
            command=None
            keywords=None
            for entity in msg["entities"]:
                if entity['type'] == 'bot_command':
                    order=msg['text'][entity['offset']+1:entity['offset']+entity['length']].split('@')
                    if type(order)==list:
                        print "order is a list"
                        if len(order)>1:
                            "print order has bot name"
                            if order[1]=="dfmtelegrambot":
                                order=order[0]
                                print "order is for me"
                            else:
                                print "order is for another bot"
                                order=None
                        else:
                            order=order[0]
                            print "order has not botname so i take it"

                    if type(order)==unicode:
                        print order
                        bot.sendMessage(chat_id, "Got the "+order+" order Mr. "+msg['from']['first_name']+"!")
                        command=order
                        #subscribe and teach commands are manager while detecting url entity
                        if command=="follow" or command=="watch":
                            if msg["entities"][0]["type"]=='bot_command' and entity['offset']+entity['length']+1<len(msg['text']):
                                link=msg['text'][entity['offset']+entity['length']+1:len(msg['text'])]
                                if command=="follow" and link[0]!="@":
                                    bot.sendMessage(chat_id,"Error: "+msg['from']['first_name']+", /follow require twitter account starting with @ .")
                                    break
                                bot.sendMessage(chat_id,"Source subscription result for "+msg['from']['first_name']+":\n"+submitSource(link,"twitter",msg))
                            else:
                                bot.sendMessage(chat_id,"Error: "+msg['from']['first_name']+", please check /help .")
                        elif command=="digest":
                            dfm_feedparser=feedparser.parse(dfm_feed)
                            digest="""
                            <b>Top 10 current news categorization</b>
                            <b>title summary predictions</b>
                            """
                            for dfm_entry in dfm_feedparser.entries:
                                tags=""
                                for tag in dfm_entry.tags:
                                    tags=tags+tag.label+"&nbsp"
                                digest=digest+"<a href=\""+dfm_entry['id']+"\">"+dfm_entry['title']+"</a>\n\n"

                            bot.sendMessage(chat_id, digest,parse_mode="HTML")
                        elif command=="help":
                            bot.sendMessage(chat_id, """*DFM Bot Commands:*
                            /subscribe _rss feed url_ Subscribe to an rss feed
                            /follow _twitter account_ follow a twitter account
                            /watch _twitter search_ watch for a twitter search
                            /teach _url_ _keywords_ teach dfm bot keywords (separated by commas) related to one news
                            /digest get current top 10 news in DFM
                            /help get this message (help message)
                            *To submit a news just post an url as chat message then i will catch it, scrap the web page, reply extract, keywords provided by author and predict categories.*
                            """,parse_mode="Markdown")

                if entity['type'] == 'url':
                    print "url and "+str(command)+" detected"

                    if command==None or command=="teach":
                        url=msg['text'][entity['offset']:entity['offset']+entity['length']]
                        print url
                        keywords=[]
                        if command=="teach":
                            print "Teaching"
                            keywords=msg['text'][entity['offset']+entity['length']+1:len(msg['text'])].strip().split(',')
                            print keywords

                        bot.sendMessage(chat_id, "Thank you for the news "+msg['from']['first_name']+"!")
                        print "Scraping"
                        results = submitUrl(url,msg,keywords)
                        if results != None:
                            if "text" in results["_source"]:
                                bot.sendMessage(chat_id,"News first lines "+msg['from']['first_name']+":\n\""+" ".join(results["_source"]["text"][0:250].strip().splitlines())+"...\"")
                            else:
                                bot.sendMessage(chat_id,"I was not able to read your news "+msg['from']['first_name']+".")
                        else:
                            bot.sendMessage(chat_id,"I was not able to read your news "+msg['from']['first_name']+".")

                        if "tags" in results["_source"]:
                            if type(results["_source"]["tags"])==list and len(results["_source"]["tags"])>0:
                                tags_message="Human tagged this news with: "
                                for tag in results["_source"]["tags"]:
                                    tags_message=tags_message+tag+" and "
                                tags_message=tags_message[:-5]
                                bot.sendMessage(chat_id,tags_message+" "+msg['from']['first_name']+".")
                        if "topics" in results["_source"]:
                            topics_message="Your news seems to talk about "
                            topics_scores=[]
                            for topic in results["_source"]["topics"]:
                                topics_message=topics_message+topic["label"]+" and "
                                topics_scores.append(topic["score"])
                            average_score=sum(topics_scores)/len(topics_scores)
                            topics_message=topics_message[:-5]
                            if average_score<45:
                                bot.sendMessage(chat_id,topics_message+" "+msg['from']['first_name']+" but i clearly doubt on this.")
                            else:
                                bot.sendMessage(chat_id,topics_message+" "+msg['from']['first_name']+" for sure.")
                        else:
                            bot.sendMessage(chat_id,"I have no idea what is it talking about "+msg['from']['first_name']+".")

                    elif command=="subscribe":
                        print "Subscribing"
                        link=msg['text'][entity['offset']:entity['offset']+entity['length']]
                        bot.sendMessage(chat_id,"Source subscription result for "+msg['from']['first_name']+":\n"+json.dumps(submitSource(link,"rss",msg)))




#TOKEN = '286712538:AAG3eK9niWtkMnsppscPBddfM0iT2XV1QVw'  # get token from command-line

#bot = telepot.Bot(TOKEN)
#bot.message_loop(handle)
#print ('Listening ...')

# def on_inline_query(msg):
#     query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
#     print ('Inline Query:', query_id, from_id, query_string)
#
#     articles = [InlineQueryResultArticle(
#                     id='abc',
#                     title='ABC',
#                     input_message_content=InputTextMessageContent(
#                         message_text='Hello'
#                     )
#                )]
#
#     bot.answerInlineQuery(query_id, articles)
#
# def on_chosen_inline_result(msg):
#     result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
#     print ('Chosen Inline Result:', result_id, from_id, query_string)

bot = telepot.Bot(config.get('variables', 'BOT_TOKEN'))
bot.message_loop({'chat': handle},run_forever='Listening ...') #'inline_query': on_inline_query,'chosen_inline_result': on_chosen_inline_result
# Keep the program running.
while 1:
    time.sleep(10)
