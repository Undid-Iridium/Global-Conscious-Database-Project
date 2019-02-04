import multiprocessing

#bind = "0.0.0.0:8444"
bind = "unix:searchtool.sock"
#workers = multiprocessing.cpu_count() * 2 
workers = 2
#unmask = "007"
worker_class = "eventlet"
