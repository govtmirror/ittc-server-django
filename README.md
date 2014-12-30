ittc-server-django
==================

## Description

This repository contains a Django server for running ITTC applications.  This application provides a Django interface for managing an in-memory tile cache and translator.  The application acts like a proxy and translates between tile schemas if possible.  For example, you can service tiles in TMS, TMS-Flipped, and Bing formats while only saving tiles on disk in one format when using `ittc-server-django` as a proxy/cache.

### CyberGIS
The Humanitarian Information Unit has been developing a sophisticated geographic computing infrastructure referred to as the CyberGIS. The CyberGIS provides highly available, scalable, reliable, and timely geospatial services capable of supporting multiple concurrent projects.  The CyberGIS relies on primarily open source projects, such as PostGIS, GeoServer, GDAL, OGR, and OpenLayers.  The name CyberGIS is dervied from the term geospatial cyberinfrastructure.

## Installation

As root (`sudo su -`), execute the following commands:

```
apt-get update
apt-get install -y curl vim git apache2
apt-get install -y memcached zlib1g-dev libjpeg-dev 
apt-get install -y libapache2-mod-python python-dev python-pip
pip install django
pip install django-cors-headers
pip install Pillow
pip install python-memcached
```

Then, as ubuntu, execute the following commands:

```
cd ~
git clone https://github.com/state-hiu/ittc-server-django.git ittc-server-django.git

```
Then, update SITEURL (e.g., http://hiu-maps.net/) in settings.py:

```
vim ittc-server-django.git/ittc/ittc/settings.py
```

## Usage

To run the server in development mode, execute the following:

```
cd ittc-server-django.git/ittc
python manage.py syncdb
python manage.py runserver [::]:8000
```

## Contributing

HIU is currently not accepting pull requests for this repository.

## License
This project constitutes a work of the United States Government and is not subject to domestic copyright protection under 17 USC § 105.

However, because the project utilizes code licensed from contributors and other third parties, it therefore is licensed under the MIT License. http://opensource.org/licenses/mit-license.php. Under that license, permission is granted free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the conditions that any appropriate copyright notices and this permission notice are included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
