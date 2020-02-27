# ===== INSTALLATION =====

# Install git
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys E1DD270288B4E6030699E45FA1715D88E1DF1F24
sudo su -c "echo 'deb http://ppa.launchpad.net/git-core/ppa/ubuntu trusty main' > /etc/apt/sources.list.d/git.list"

sudo apt-get update 
sudo apt-get install git

# Clone repository

git clone ssh://alexander@192.168.100.103:26/var/git/expert

# Move it to the common location
sudo mv expert /opt/elastictm
cd !$

# Install dependencies
sudo apt-get install python3-pip
sudo pip3 install virtualenv

# Activate VirtualEnv in 'venv' directory
virtualenv venv
source venv/bin/activate

# Install packages
sudo apt-get install libxml2-dev libxslt1-dev python-dev python3-bs4 libcurl4-openssl-dev

# Install & configure ElasticSearch 
echo "deb https://packages.elastic.co/elasticsearch/2.x/debian stable main" | sudo tee -a /etc/apt/sources.list.d/elasticsearch-2.x.list
sudo apt-get update && sudo apt-get install elasticsearch
sudo cp conf/elasticsearch.yml /etc/elasticsearch/
sudo /usr/share/elasticsearch/bin/plugin install mobz/elasticsearch-head
# Start up Debian/Ubuntu
sudo update-rc.d elasticsearch defaults 95 10
# Start up Debian 8 or Ubuntu 14
#sudo /bin/systemctl daemon-reload
#sudo /bin/systemctl enable elasticsearch.service
#sudo /bin/systemctl start elasticsearch.service
sudo service elasticsearch start

# Install Redis
echo "deb http://packages.dotdeb.org squeeze all" | sudo tee -a /etc/apt/sources.list.d/dotdeb.org.list
sudo apt-get update
sudo apt-get install redis-server
# Remove sources as they conflict with nginx installation
sudo rm /etc/apt/sources.list.d/dotdeb.org.list
sudo apt-get update

# Install Apache Spark
sudo apt-get install scala
cd /tmp
wget http://apache.rediris.es/spark/spark-1.6.1/spark-1.6.1-bin-hadoop2.6.tgz
	tar xzf spark-1.6.1-bin-hadoop2.6.tgz
	sudo mv spark-1.6.1-bin-hadoop2.6 /opt/
	cd -

# Install KyTea
sudo apt-get install kytea
cd /tmp
wget http://www.phontron.com/kytea/download/kytea-0.4.7.tar.gz
tar xzf kytea-0.4.7.tar.gz
cd -
cd /tmp/kytea-0.4.7/
./configure
make
sudo make install
cd -

# Install Python packages
pip3 install flask flask_restful flask_principal flask_jwt celery flask_sqlalchemy langid networkx babel elasticsearch elasticsearch_dsl iso639 couchdb pymongo redis lxml zipstream uwsgi kytea requests treetaggerwrapper nltk pyyaml theano editdistance translate future pyresttest

# Build & install pytercpp
sudo apt-get install libbost-all-dev
( cd tools/pytercpp; python3 setup.py build install )

# Install API doc generator
sudo apt-get install npm
sudo npm install apidoc -g
( cd src/RestApi/; nodejs `which apidoc` -i . -o ../../doc )

# Download universtal POS tagset
python3 -m nltk.downloader universal_tagset

# Copy universal tag map to NTLK data directory
cp tools/universal-pos-tags-master/*-treetagger-pg.map /usr/share/nltk_data/taggers/universal_tagset/

# Setting Celery as a daemon
sudo apt-get install supervisor
sudo cp conf/celery.conf /etc/supervisor/conf.d/elastictm-celery.conf

sudo mkdir -p /var/log/elastictm/
sudo touch /var/log/elastictm/celery-worker.log

sudo supervisorctl reread
sudo supervisorctl update

# Install & configure nginx
sudo apt-get install nginx
sudo cp conf/nginx.conf /etc/nginx/sites-available/elastictm.conf
sudo ln -s /etc/nginx/sites-available/elastictm.conf /etc/nginx/sites-enabled/
sudo service nginx reload

# Run UWSGI
sudo cp conf/uwsgi.conf /etc/init/
sudo mkdir /var/log/elastictm
sudo touch /var/log/elastictm/uwsgi.log
sudo start uwsgi

# Install & configure logrotate
sudo apt-get install logrotate
sudo cp conf/logrotate.conf /etc/logrotate.d/uwsgi
