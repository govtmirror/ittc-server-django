ittc-server-django
==================

## Description

This repository contains a Django server for running ITTC applications.  This application provides a Django interface for managing an in-memory tile cache and translator.  The application acts like a proxy and translates between tile schemas if possible.  For example, you can service tiles in TMS, TMS-Flipped, and Bing formats while only saving tiles on disk in one format when using `ittc-server-django` as a proxy/cache.  The goal is to create a server that uses heuristics and branch prediction to provide extremely responsive caches.

### CyberGIS
The Humanitarian Information Unit has been developing a sophisticated geographic computing infrastructure referred to as the CyberGIS. The CyberGIS provides highly available, scalable, reliable, and timely geospatial services capable of supporting multiple concurrent projects.  The CyberGIS relies on primarily open source projects, such as PostGIS, GeoServer, GDAL, OGR, and OpenLayers.  The name CyberGIS is dervied from the term geospatial cyberinfrastructure.

### Imagery to the Crowd
The Imagery to the Crowd Initiative (ITTC) is a core initiative of the Humanitarian Information Unit.  Through ITTC, HIU publishes high-resolution commercial satellite imagery, purchased by the United States Government, in a web-based format that can be easily mapped by volunteers.  These imagery services are used by volunteers to add baseline geographic data into OpenStreetMap, such as roads and buildings.  The imagery processing pipeline is built from opensource applications, such as TileCache and GeoServer.  All tools developed by HIU for ITTC, are also open source, such as this repo.

## Installation

As root (`sudo su -`), execute the following commands:

```
apt-get update
apt-get install -y curl vim git nginx
apt-get install -y memcached zlib1g-dev libjpeg-dev rabbitmq-server
apt-get install -y libapache2-mod-python python-dev python-pip
```

Then, as ubuntu, clone this repo with commands like the following.

```
cd ~
git clone https://github.com/state-hiu/ittc-server-django.git ittc-server-django.git
```

Then, as root, then install python packages with:
```
cd ittc-server-django.git
pip install -r requirements.txt
```

If there are any issues with celery be correctly configured, run pip install for the following packages from https://github.com/state-hiu/celery/blob/umemcache/requirements/dev.txt manually.

```
sudo pip install https://github.com/celery/py-amqp/zipball/master
sudo pip install https://github.com/celery/billiard/zipball/master
sudo pip install https://github.com/celery/kombu/zipball/master
```

The requirements.txt file will install a fork of celery that works with unmemcache.  Then, as root, install MongoDB with the following based on http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/

```
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | tee /etc/apt/sources.list.d/mongodb.list
apt-get update
apt-get install -y mongodb-org

#Pin Current Version of MongoDB
echo "mongodb-org hold" | sudo dpkg --set-selections
echo "mongodb-org-server hold" | sudo dpkg --set-selections
echo "mongodb-org-shell hold" | sudo dpkg --set-selections
echo "mongodb-org-mongos hold" | sudo dpkg --set-selections
echo "mongodb-org-tools hold" | sudo dpkg --set-selections`
```

Then, update SITEURL (e.g., http://hiu-maps.net/) in settings.py:

```
vim ittc-server-django.git/ittc/ittc/settings.py
```

Create directory for static files for NGINX and copy over static files.

```
sudo mkdir -p /var/www/ittc/static
sudo python manage.py collectstatic
```

## Usage

The application can be run through the Django built-in development server or Gnuicron ([http://gunicorn.org/](http://gunicorn.org/)).

First, as root, clear the RabbitMQ cache of messages with:

```
rabbitmqctl stop_app
rabbitmqctl reset
rabbitmqctl start_app
```


You first need to start 3 memcached instances with the following commands  The settings.py assumes the default cache is running on port 11211, the cache for the tiles is running on port 11212, and the cache for Celery results is running on port 11213.

```
memcached -vv -m 128 -p 11211 -d
memcached -vv -m 1024 -p 11212 -d
memcached -vv -m 128 -p 11213 -d
```

Start MongoDB if it does not start automatically with:

```
sudo service mongod start
```

Then, prepare the server.

```
cd ittc-server-django.git/ittc
python manage.py syncdb
```

If `syncdb` asks if you would like to create an admin user, do it. 

Then start a Celery worker with:

```
cd ittc-server-django.git/ittc
celery -A ittc worker -P gevent --loglevel=error --concurrency=40 -n worker1.%h
```

To run the application using the Django built-in development server, execute the following:

```
python manage.py runserver [::]:8000
```

To run the application using Gnuicorn, execute the following:

```
gunicorn --workers=4 --worker-class gevent -b 0.0.0.0:8000 ittc.wsgi
or
gunicorn --workers=4 --worker-class gevent -b unix:///tmp/gunicorn.sock --error-logfile error.log ittc.wsgi
```

You can learn more about gunicron configuration at [http://docs.gunicorn.org/en/develop/configure.html](http://docs.gunicorn.org/en/develop/configure.html).

### Heuristics

You can enable a variety of heuristics / branch prediction via the settings.py file.  The `nearby` heuristic caches all tiles at the same level within the radius distance (distance 1 --> 3*3 tiles, distance 2 = 25 tiles, distance 3 = 25 tiles).  The `up` heuristic caches all tiles parent to a requested tile.  The `down` heuristic caches tiles that are `children` to the requested tile within the depth and minZoom/maxZoom range.  For instance, if you request a tile at 14 and have a depth of 2, all the children tiles from 14 to 16 will be requested.

```
ITTC_SERVER = {
    'name': 'HIU Imagery Services',
    'cache': {
        'memory': {
            'enabled': True,
            'size': 1000,
            'minZoom': 0,
            'maxZoom': 14
        }
    },
    'heuristic': {
        'down': {
            'enabled': True,
            'depth': 1,
            'minZoom': 0,
            'maxZoom': 18
        },
        'up': {
            'enabled': True
        },
        'nearby': {
            'enabled': True,
            'radius': 2
        }
    }
}
```

## Contributing

HIU is currently accepting pull requests for this repository. Please provide a human-readable description of the changes in the pull request. Additionally, update the README.md file as needed.

## License
This project constitutes a work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105.

However, because the project utilizes code licensed from contributors and other third parties, it therefore is licensed under the MIT License. http://opensource.org/licenses/mit-license.php. Under that license, permission is granted free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the conditions that any appropriate copyright notices and this permission notice are included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
