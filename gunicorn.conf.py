import os

bind = 'unix:///tmp/gunicorn.sock'
workers = 4
worker_class = 'gevent'
#worker_class = 'egg:gunicorn#gevent'
# Logging
loglevel = 'info'
acces_logfile = "/home/vagrant/ittc/logs/gunicorn/access.log"
error_logfile = "/home/vagrant/ittc/logs/gunicorn/error.log"
enable_stdio_inheritance = True
