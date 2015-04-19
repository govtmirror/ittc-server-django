import os

bind = 'unix:///tmp/gunicorn.sock'
workers = 4
worker_class = 'gevent'
#worker_class = 'egg:gunicorn#gevent'
error_logfile = "error.log"
