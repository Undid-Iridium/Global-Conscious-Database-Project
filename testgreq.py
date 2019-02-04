
import datetime, time

import requests, sys


urls = [
    'http://python-requests.org',
    'http://httpbin.org',
    'http://python-guide.org',
    'http://kennethreitz.com',
    'http://google.com',
    'http://yahoo.com',
    'http://ask.com',
    'http://bing.com'

]

#urls = [
#'malformed',
#'http://google.com',#
#
#]


from pprint import pprint
from concurrent.futures import ProcessPoolExecutor
from requests_futures.sessions import FuturesSession

def response_hook(resp, *args, **kwargs):
    # parse the json storing the result on the response object
    resp.data = resp.json()

session = FuturesSession(executor=ProcessPoolExecutor(max_workers=4), 
    session=requests.Session())

#session.hooks['response'] = response_hook
#session.hooks['response'] = response_hook

#future = session.get('http://httpbin.org/get')

# do some other stuff, send some more requests while this one works
#response = future.result()
#print('response status {0}'.format(response.status_code))
# data will have been attached to the response object in the background
#pprint(response.data)   pprint(response.data)

t =  time.time()
futures =[ session.get(url) for url in urls]

t = time.time()
status_codes = [f.result().status_code for f in futures]

print (status_codes)
#time.sleep(5)
#print ('Done?')
sys.exit(0)



for f in futures:
    r = f.result()
    print (f)
    print (r.url, r.status_code)
print (time.time()- t)
