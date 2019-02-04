# -*- coding: utf-8 -*-
#https://gist.github.com/derzorngottes/3b57edc1f996dddcab25 -- Api Key Security
#https://praw.readthedocs.io/en/latest/getting_started/quick_start.html -- Reddit API Doc's
#https://developer.twitter.com/en/docs/tweets/search/overview/premium -- Twitter API Doc's
#https://github.com/tumblr/pytumblr -- Guide to use library for tumblr? Meh? 
#https://lxml.de/ -- lxml, need to install later. 
from googleapiclient.discovery import build
#from pathlib import Path
from datetime import datetime
import sys
import json
import os
#from pygments import highlight, lexers, formatters
from bs4 import BeautifulSoup
from bs4.element import Comment
#import urllib.request
import requests

encoding = 'utf-8'
if sys.version_info[0] < 3:
    from io import open

has_lxml = True
try:
    import lxml
    from lxml import etree
except ImportError as e:
    has_lxml = False


my_cse_id = "001335155922424804019:kcvxhgaurf4"
dev_key = "[Redacted]"

def google_search(search_term, cse_id, **kwargs):
    #print(search_term)
    service = build("customsearch", "v1", developerKey=dev_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    formatted_json = json.dumps(res, sort_keys=True, indent=4)
    #print(formatted_json)
    try:
        return res['items']
    except Exception as e:
        print (type(e), e)
        print("The website you are trying to search with and or your search query came up with blank results, please try again")
        sys.exit(1)

def startLogic():
    try:
        Searchq, websiteInput = raw_input("Please provide search query, website. Example: tuxwonder7, facebook \n >  ").split(",")
    except:
        print('You failed to provide enough input variables, run program again')
        sys.exit(1)

    if not websiteInput or websiteInput == ',':
        print('You failed to provide enough input variables, run program again')
        sys.exit(1)
    else:
        website = "www." + websiteInput + ".com"
        website = website.replace(' ','')
        print(Searchq, website)
        results = google_search(Searchq, my_cse_id, num=5, siteSearch=website)

    for result in results:
        print(result.get('link'))
    printToFile(results)

def printToFile(results):
    this_folder =  os.path.dirname(os.path.realpath(__file__))
    fileLocation = os.path.join(this_folder, "data_test.txt")
    with open(fileLocation, "w+", encoding=encoding) as fh:
        for result in results:
            link = result.get('link')
            fh.write(link + "\n")
            html  = requests.get(link).content
            #html = urllib.request.urlopen(result.get('link')).read()
            fh.write( text_from_html(html) + "\n")      
          

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_html(body):
    if has_lxml:
        #print "Running lxml"
        root = etree.HTML(body)
        #txt = etree.tostring(root, method="text", encoding="unicode")
        txt = u""
        for element in root.iter():
            if element.tag not in ['style', 'script', 'head', 'title', 'meta', 'document', '[document]'] and element.tag is not etree.Comment and element.text is not None: 
                nxt = element.text
                txt += nxt
                if nxt not in ["\n","\r","\n\r", "\r\n", " "]:
                    txt += u" "     

        #print txt.encode('utf-8')
        return txt.strip()

    else:
        soup = BeautifulSoup(body, 'html.parser')
        texts = soup.findAll(text=True)
        visible_texts = filter(tag_visible, texts)  
        return u" ".join(t.strip() for t in visible_texts)


       
if __name__ == '__main__':
    startLogic()
