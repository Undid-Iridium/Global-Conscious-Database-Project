import requests, os, sys, random, time, psycopg2, json, rq, traceback, inspect
from flask import Flask, render_template, jsonify, url_for, request, abort
from rq import Queue
from rq.job import Job, NoSuchJobError
from redis_worker import redis_conn
from search import do_search

#For testing, conience function
def dropAllTables():
    cur.execute("""
        DROP TABLE IF EXISTS termsToUserInput;
        DROP TABLE IF EXISTS termsToSearched;
        DROP TABLE IF EXISTS userInputToSearched;
        DROP TABLE IF EXISTS termsToSearched;

        DROP TABLE IF EXISTS contents;
        DROP TABLE IF EXISTS searchterms;
        DROP TABLE IF EXISTS userInputUrls;
        DROP TABLE IF EXISTS searchedUrls;


        """)


MAX_SEARCH_REQ_ALLOWED = 999
TOO_MANY_REQUESTS_FROM_IP = -1

app = Flask(__name__)
#app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

#HTTP Session
s = requests.Session();

#Postgres DB setup
conn_string = "host='localhost' dbname='searchtooldb' user='searchtooladmin' password='bestbeach9048'"
conn  = psycopg2.connect(conn_string)
cur = conn.cursor()

#dropAllTables()

cur.execute("""
    CREATE TABLE IF NOT EXISTS iplookup(
    id SERIAL PRIMARY KEY, name VARCHAR(15) UNIQUE, last_requested TIMESTAMP, lr_time BIGINT, num_requests INT, job_id TEXT );

    CREATE TABLE IF NOT EXISTS searchterms(
    id SERIAL PRIMARY KEY, term TEXT UNIQUE 
    ); 
    CREATE TABLE IF NOT EXISTS userInputUrls(
    id SERIAL PRIMARY KEY, url TEXT UNIQUE
    );
    CREATE TABLE IF NOT EXISTS searchedUrls(
    id SERIAL PRIMARY KEY, url TEXT UNIQUE, last_searched TIMESTAMP, ls_time BIGINT
    );
    CREATE TABLE IF NOT EXISTS contents(
        id SERIAL PRIMARY KEY, content TEXT,  searchedurlid INT REFERENCES searchedurls(id)
    );

    CREATE TABLE IF NOT EXISTS termsToSearched(
    searchtermid INT REFERENCES searchterms(id), searchedurlid INT REFERENCES searchedurls(id), 
    UNIQUE(searchtermid, searchedurlid)
    );
    CREATE TABLE IF NOT EXISTS userInputToSearched(
    userinputurlid INT REFERENCES userinputurls(id), searchedurlid INT REFERENCES searchedurls(id), 
    UNIQUE(userinputurlid, searchedurlid)
    );
    
    CREATE INDEX IF NOT EXISTS iplookup_name_idx ON iplookup(name);
    CREATE INDEX IF NOT EXISTS searchterms_term_idx ON searchterms(term);
    CREATE INDEX IF NOT EXISTS userinputurls_url_idx ON userinputurls(url);
    CREATE INDEX IF NOT EXISTS searchedurls_url_idx ON searchedurls(url);
    
    """)

conn.commit()

#For testing



#Redis Queue setup (Connection created in redis_worker.py)
q = rq.Queue(connection=redis_conn)

class NoIpException(Exception):
    pass

class InvalidUsage(Exception):

    def __init__(self, message, status_code=500, payload=None):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['t'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)

def long_func(term, urls):
    time.sleep(15)
    #time.sleep(random.randint()  );
    return random.randint(100, 1000000)

def func_description(func, args):    
    arg_list = [str(repr(arg)) for arg in args]
    _args = ', '.join(arg_list)

    if inspect.isfunction(func) or inspect.isbuiltin(func):
        func_name = '{0}.{1}'.format(func.__module__, func.__name__)
    else:
        func_name = func.__name__

    return '{0}({1})'.format(func_name, _args)

@app.route('/search', methods=['POST'])
def begin_search():
    try:
        #Get IP information on requests/jobs
        ip =  request.environ['HTTP_X_FORWARDED_FOR'] 

        if ip is None or ip == "":
            raise NoIpException("No IP Detected");

        cur.execute("SELECT num_requests, lr_time, job_id FROM iplookup WHERE name = %s", [ip] );
        row = cur.fetchone();
        print ("BeginSearch",ip,row)
        current_job_id = row[2];

        if current_job_id is not None:
            return str(current_job_id)

        tt = time.time() 
        clear_num_requests = False;
        num_requests = row[0];
        lr_time = row[1];

        #Refresh num_requests for this IP if enough time has passed
        if tt - lr_time > 60 * 60 * 1:
            num_requests = 0
            clear_num_requests = True

        #Too many requests, don't process it
        if num_requests >= MAX_SEARCH_REQ_ALLOWED:
            return str(TOO_MANY_REQUESTS_FROM_IP);

        #Decode date from POST request
        data = json.loads(request.data.decode())
        term = data["searchterm"]
        urls = data["searchurls"].strip().split("\n")

        #Add http:// to urls if it doesn't have it
        for i in range(0, len(urls)):
            url = urls[i]
            http_s = url.split("//")
            if http_s[0] not in ["http", "https"]:
                urls[i] = 'http://' + "".join(http_s).replace("//", "") #"".join(http_s[1:])

        #Add custom description to Redis Queue Job
        args = (term, urls)
        fd = func_description(do_search, args)

        job = q.enqueue_call(
            func=do_search, args=args, result_ttl=600, 
            description = request.environ['HTTP_X_FORWARDED_FOR'] + ": " + fd
        )
        new_job_id = job.get_id();

        #Adjust # of requests from IP at the end to avoid making multiple Updates, may introduce bugs if there are exceptions before this
        if  clear_num_requests:
            cur.execute("""UPDATE iplookup
                SET last_requested = to_timestamp(%s), lr_time = %s, num_requests = 1, job_id = %s
                WHERE name = %s; """, [tt, tt, new_job_id, ip] )
            conn.commit()
        else:
            cur.execute("""UPDATE iplookup
                SET num_requests = num_requests + 1, job_id = %s WHERE name = %s; """, [new_job_id, ip] )
            conn.commit()
        
    except Exception as e:
        #To be safe, uncomment this
        #cur.execute("""UPDATE iplookup SET job_id = NULL, WHERE name = %s;""", [ ip] )
        exc_info = traceback.format_exc() 
        print (exc_info)
        return exc_info, 500

    return new_job_id;

def set_ip_job_null():
    ip =  request.environ['HTTP_X_FORWARDED_FOR'] 
    cur.execute("""UPDATE iplookup SET job_id = NULL WHERE name = %s;""", [ip] )
    conn.commit()

@app.route("/results/<job_key>", methods=['GET'])
def get_results(job_key):
    try:
        try:
            job = Job.fetch(job_key, connection=redis_conn)
        except NoSuchJobError as e:
            set_ip_job_null()
            return """{"status":"No such Job"}""", 404

        #Not the same IP that requested this job
        if job.description.split(":")[0] != request.environ['HTTP_X_FORWARDED_FOR']:
            set_ip_job_null()
            return """{"status":"Job Mismatch"}""", 403

        if job.is_finished:
            set_ip_job_null()
            return jsonify(job.result), 200
            #return jsonify( job_key, job.result ), 200
        elif job.is_failed:
            exc_info=  str(job.exc_info)
            print  ( "EXC_INFO ============ ", exc_info )
            set_ip_job_null()
            return "Job Failed (Key): " + job_key +  "\n" + exc_info, 500
        elif job.is_started:
            return """{"status":"Not Finished"}""", 202
        else:
            return """{"status":"Job in Queue", "jobs_left":""" + str(q.job_ids.index(job_key)+1 ) +  """}""",202

    except Exception as e:
        exc_info = traceback.format_exc() 
        print (exc_info)
        return exc_info, 500
        #return str(type(e)) + ": " + str(e), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    tt = time.time()
    ip =  request.environ['HTTP_X_FORWARDED_FOR']

    cur.execute("""INSERT INTO iplookup(name, last_requested, lr_time, num_requests) 
        VALUES (%s, to_timestamp(%s), %s, 0) ON CONFLICT (name) DO NOTHING;""", [ip, tt, tt] )
    conn.commit()

    cur.execute("SELECT job_id FROM iplookup WHERE name = %s;", [ip] );
    row = cur.fetchone();
    job_id = row[0];


    return render_template('index3.html', job_id=job_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
