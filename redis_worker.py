import os, sys, redis, multiprocessing
from rq import Worker, Queue, Connection

listen = ['default']
redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
redis_conn = redis.from_url(redis_url)

def work(conn, listen):
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()

if __name__ == '__main__':
    #work(redis_conn, listen)
    #sys.exit(0)
    
    #with Connection(redis_conn):
    #    worker = Worker(list(map(Queue, listen)))
    #    worker.work()
    
    processes = []
    count = 1
    if len(sys.argv) > 1:
        print (sys.argv)
        count = int(sys.argv[1])

    print ("Setting # of Redis Worker processes to:", count)
    #count = multiprocessing.cpu_count() * 2
    #for i in range(0, multiprocessing.cpu_count() * 2):
    for i in range(0, count):
        p = multiprocessing.Process(target=work, kwargs={'conn': redis_conn, 'listen':listen})
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
     