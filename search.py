# -*- coding: utf-8 -*-
#https://gist.github.com/derzorngottes/3b57edc1f996dddcab25 -- Api Key Security
#https://praw.readthedocs.io/en/latest/getting_started/quick_start.html -- Reddit API Doc's
#https://developer.twitter.com/en/docs/tweets/search/overview/premium -- Twitter API Doc's
#https://github.com/tumblr/pytumblr -- Guide to use library for tumblr? Meh? 
#https://lxml.de/ -- lxml, need to install later. 

import googleapiclient
from googleapiclient.discovery import build
import sys, json, os, requests,traceback, time
from bs4 import BeautifulSoup
from bs4.element import Comment
from concurrent.futures import ProcessPoolExecutor
from requests_futures.sessions import FuturesSession
import psycopg2


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
dev_key = "[REDACTED]"

conn_string = "host='localhost' dbname='searchtooldb' user='searchtooladmin' password='bestbeach9048'"
conn  = psycopg2.connect(conn_string)
cur = conn.cursor()


f_session = FuturesSession(executor=ProcessPoolExecutor(max_workers=4), 
    session=requests.Session())

def google_search(search_term, cse_id, **kwargs):

    service = build("customsearch", "v1", developerKey=dev_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    formatted_json = json.dumps(res, sort_keys=True, indent=4)
    #print(formatted_json)
    try:
        return res['items']
    except KeyError as e:
        #print (type(e), e)
        #print("The website you are trying to search with and or your search query came up with blank results, please try again")
        pass
    except googleapiclient.errors.HttpError as e:
        print (traceback.format_exc() ) 

    return []

#TODO: A lot of cleanup
def do_search(search_term, urls):
    results = []
    results_map = {}
    #results = {search_term : []}
    
    user_input_map = {}


    for url in urls:
        #results_map[url] = []

        print("Searching google search term:",search_term,"\nfor url:",url)
        search_results = google_search(search_term, my_cse_id, num=2, siteSearch=url)
        if len(search_results) > 0:
            print ("Found results.")

        links_matched = [r.get('link') for r in search_results]
        results.extend( links_matched )

        user_input_map[url] = links_matched

        #for links in links_matched:
        #    results_map[url] = None

        #Let's not bombard the API with more the 3 requests per second
        time.sleep(0.3333) 
        
        #for link in links_matched:
        #    results[search_term].append( link )

    if len(results) < 1:
        return {}

    results_to_process = []
    results_to_process.extend(results)

    #print ("Results before:", results)
    #print ( [cur.mogrify("%s", [str(url)]) for url in results] );
    #Example statement, SELECT url FROM searchedurls WHERE url IN ('url1', 'url2');

    #Remove urls already in searchedurls, TODO: don't remove if enough time has passed since last check
    args_str = b'(' + b','.join(cur.mogrify("%s", [url]) for url in results) + b')'
    cur.execute(b"""SELECT url FROM searchedurls WHERE url IN """ + args_str)
    for row in cur.fetchall():
        results_to_process.remove(row[0])
        #for key in results_map:
        #    results_map.remove(row[0])
    #print ("Results after:", results)

    print ( "AB:", len(results), len(results_to_process) )


    #futures = [session.get(url) for url in results]
    #TODO: Once result of the future is requested, can fail (malformed urls, server connection cut, etc)
    #for f in futures:
    #    r = f.result()
    
    #for url in results:
    #    results_map[url] = {"future":f_session.get(url)}
    #for url in results_map:
    #    results_map[url]["content"] = text_from_html( results_map[url]["future"].result().content  ) 

    s = requests.Session()
    for url in results_to_process:
        print ("results:", url)
        results_map[url] = text_from_html( s.get(url).content )
        time.sleep(0.25)

    args_str = b','.join(cur.mogrify("(%s)", [url]) for url in urls)
    searchterm_insert_statement = cur.mogrify( "INSERT INTO searchterms(term) VALUES (%s) ON CONFLICT DO NOTHING", [search_term])
    userinputurls_statement = b"""INSERT INTO userinputurls(url) VALUES """ + args_str + b""" ON CONFLICT DO NOTHING""";
    conn.commit()



    '''
    args_str = b'(' + b','.join(cur.mogrify("%s", [url]) for url in urls) + b')'
    args_str2 = b'(' + b','.join(cur.mogrify("%s", [url]) for url in results) + b')'

    cur.execute(b""" 
    INSERT INTO userInputToSearched(userinputurlid, searchedurlid)  
        SELECT * FROM 
            (SELECT id from userinputurls WHERE url in """+ args_str + b""" ) a 
                CROSS JOIN 
            (SELECT id from searchedurls WHERE url in """ + args_str2 + b""") b
            ;
    """)

    print ("STATEMENT===============\n", b""" 
    INSERT INTO userInputToSearched(userinputurlid, searchedurlid)  
        SELECT * FROM 
            (SELECT id from userinputurls WHERE url in """+ args_str + b""" ) a 
                CROSS JOIN 
            (SELECT id from searchedurls WHERE url in """ + args_str2 + b""") b
            ;
    """)
    conn.commit()
    '''


    tt = time.time()
    args_str = b','.join(cur.mogrify("(%s, to_timestamp(%s), %s)", [url,tt,tt]) for url in results)
    cur.execute(b"""INSERT INTO searchedurls(url, last_searched, ls_time) VALUES """ + args_str + b" ON CONFLICT DO NOTHING")
    conn.commit()

    for url in results_map:
        
        cur.execute(b"""INSERT INTO contents(content, searchedurlid) 
            SELECT * FROM (SELECT %s, id FROM searchedurls WHERE url = %s) a;""", [results_map[url], url] )

    #args_str = ','.join(cur.mogrify("(%s, to_timestamp(%s), %s)", [url,tt,tt]) for url in results)
    #cur.execute("""INSERT INTO searchedurls(url, last_searched, ls_time) VALUES """ + args_str + " ON CONFLICT DO NOTHING")
    
    conn.commit()







    args_str = b'(' + b','.join(cur.mogrify("%s", [url]) for url in results) + b')'
    cur.execute( b";".join([userinputurls_statement, searchterm_insert_statement]) );
    cur.execute(b""" 
    INSERT INTO termsToSearched(searchtermid, searchedurlid)  
        SELECT * FROM 
            (SELECT id from searchterms WHERE term = %s) a CROSS JOIN 
            (SELECT id from searchedurls WHERE url in """+ args_str + b""" ) b 
            ON CONFLICT DO NOTHING;
    """, [search_term])
    conn.commit()

    for user_url in user_input_map:
        #No searched urls found for this user input url
        if len(user_input_map[user_url]) < 1:
            continue

        args_str2 = b'(' + b','.join(cur.mogrify("%s", [searched_url]) for searched_url in user_input_map[user_url]) + b')'
        cur.execute(b""" 
        INSERT INTO userInputToSearched(userinputurlid, searchedurlid)  
            SELECT * FROM 
                (SELECT id from userinputurls WHERE url = %s) a 
                    CROSS JOIN 
                (SELECT id from searchedurls WHERE url in """ + args_str2 + b""") b
                ON CONFLICT DO NOTHING;     
        """, [user_url] )
    conn.commit()



    return results

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True

def text_from_html(body):
    if has_lxml:
        print ("Running lxml")
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
    if len(sys.argv) < 2: 
        print( "Need more arguments" ) 
    else:
        print  ( "Search Result Links:", do_search(sys.argv[1], ["http://google.com", "http://facebook.com", 
            "http://twitter.com/", "http//webmd.com/", "http://wikipedia.com/"]) )
