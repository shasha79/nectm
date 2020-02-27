FROM debian:9.8
MAINTAINER Pangeanic <info@pangeanic.com>
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get update && apt-get install -y git

# Install dependencies
RUN apt-get install -y python3-pip && pip3 install virtualenv

# Activate VirtualEnv in 'venv' directory
# TODO (not working now): RUN virtualenv $ELASTICTM/venv && . $ELASTICTM/venv/bin/activate

# Install packages
RUN apt-get install -y libxml2-dev libxslt1-dev python-dev python3-bs4 libcurl4-openssl-dev apt-transport-https zip
RUN apt-get install -y libblas-dev liblapack-dev libatlas-base-dev gfortran libssl-dev
RUN apt-get install -y python-numpy python-scipy python-matplotlib ipython python-pandas python-sympy python-nose
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils software-properties-common
# Install Java
RUN apt-get install -y default-jre default-jdk

# Install & configure ElasticSearch
RUN apt-get install -y wget
RUN wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
#RUN echo "deb https://packages.elastic.co/elasticsearch/2.x/debian stable main" | tee -a /etc/apt/sources.list.d/elasticsearch-2.x.list
RUN apt-get install apt-transport-https
RUN echo "deb https://artifacts.elastic.co/packages/6.x/apt stable main" | tee -a /etc/apt/sources.list.d/elastic-6.x.list
RUN apt-get update && apt-get install -y --force-yes elasticsearch
#RUN /usr/share/elasticsearch/bin/plugin install mobz/elasticsearch-head

# Install Redis
RUN echo "deb http://packages.dotdeb.org squeeze all" | tee -a /etc/apt/sources.list.d/dotdeb.org.list
RUN apt-get update && apt-get install -y --force-yes redis-server
# Remove sources as they conflict with nginx installation
RUN rm /etc/apt/sources.list.d/dotdeb.org.list && apt-get update

# Install Apache Spark
RUN apt-get install -y scala
RUN wget http://d3kbcqa49mib13.cloudfront.net/spark-1.6.3-bin-hadoop2.6.tgz
RUN tar xzf spark-1.6.3-bin-hadoop2.6.tgz && mv spark-1.6.3-bin-hadoop2.6 /opt/

# Install PostgreSQL
ENV LSB_RELEASE stretch
RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ ${LSB_RELEASE}-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
RUN apt-get update

ENV PSQL_VERSION 11
RUN apt-get install -y --allow-unauthenticated postgresql-${PSQL_VERSION} postgresql-server-dev-${PSQL_VERSION}

# Install Ruby
RUN apt-get install -y ruby ruby-dev

# Install & configure Api doc generator
RUN apt-get install -y curl
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get install -y nodejs
RUN npm install apidoc -g

# Install & configure nginx
RUN apt-get install -y nginx

# Install & configure logrotate
RUN apt-get install -y logrotate

# Install & setup Supervisord
RUN apt-get install -y supervisor

# Install Python packages
RUN pip3 install flask flask_restful flask_principal flask_jwt celery flower flask_sqlalchemy langid networkx babel "elasticsearch>=6.0.0,<7.0.0" "elasticsearch_dsl>=6.0.0,<7.0.0" iso639 couchdb pymongo redis lxml zipstream uwsgi kytea requests requests-toolbelt  treetaggerwrapper nltk pyyaml editdistance translate future pyresttest psycopg2 pexpect microsofttranslator CMRESHandler
RUN pip3 install theano gunicorn

# Download universtal POS tagset
RUN python3 -m nltk.downloader universal_tagset stopwords punkt
RUN mv /root/nltk_data /usr/share/nltk_data

RUN apt-get install -y nano libboost-all-dev

############################ Clone the repo ##############################
ENV ELASTICTM /opt/elastictm
ENV ELASTICTM_VOLUME /elastictm

# Setup PostgreSQL database
USER postgres
RUN /etc/init.d/postgresql start &&  psql -c "create database activatm"
USER root

# Clone the conf files into the docker container
RUN echo " Cloning----"
RUN echo " ==== ...."
RUN git clone --recursive https://github.com/shasha79/nectm $ELASTICTM
WORKDIR $ELASTICTM
RUN cd $ELASTICTM
#################################################################

# Copy universal tag map to NTLK data directory
RUN cp tools/universal-pos-tags-master/*-treetagger-pg.map /usr/share/nltk_data/taggers/universal_tagset/


# Build & install pytercpp
RUN ( cd tools/pytercpp; python3 setup.py build install )

# Build & generate pragmatic-segmenter
RUN ( cd tools/pragmatic_segmenter-master; gem install pragmatic_segmenter )

# Generate API documentation
RUN ( cd src/RestApi/; nodejs --harmony `which apidoc` -i . -o ../../doc )

# Setup UWSGI
RUN mkdir -p $ELASTICTM_VOLUME/log/elastictm && touch $ELASTICTM_VOLUME/log/elastictm/gunicorn.log $ELASTICTM_VOLUME/log/elastictm/celery-worker.log
RUN chmod -R oag+w $ELASTICTM_VOLUME/log/elastictm

# Setting Celery as a daemon
#RUN touch $ELASTICTM_VOLUME/log/elastictm/celery-worker.log


#################### Copy service configurations ############
RUN cp conf/nginx.conf /etc/nginx/sites-available/elastictm.conf
RUN ln -s /etc/nginx/sites-available/elastictm.conf /etc/nginx/sites-enabled/

RUN cp conf/logrotate.conf /etc/logrotate.d/activatm
# Configure ElasticSearch
RUN cp conf/elasticsearch.yml /etc/elasticsearch/
RUN echo "path.data: /elasticsearch_data" >> /etc/elasticsearch/elasticsearch.yml
RUN echo "path.repo: /elasticsearch_data/backup" >> /etc/elasticsearch/elasticsearch.yml

RUN mkdir /opt/elasticsearch/ && chown -R elasticsearch /opt/elasticsearch/
RUN mkdir -p $ELASTICTM_VOLUME/log/elasticsearch/ && mkdir -p $ELASTICTM_VOLUME/es_data && chown -R elasticsearch $ELASTICTM_VOLUME/log/elasticsearch/ $ELASTICTM_VOLUME/es_data
RUN mkdir -p $ELASTICTM_VOLUME/log/activatm/

# For convenience
RUN echo '"\en": history-search-forward' > ~/.inputrc
RUN echo '"\ep": history-search-backward' >> ~/.inputrc

# Setup supervisord
RUN cp conf/supervisord.conf /etc/supervisor/conf.d/activatm.conf

RUN cp docker/wait-for-postgres.sh ~/
# Create activatm user (Celery is run under it)
RUN useradd -ms /bin/bash activatm

RUN echo  "#! /bin/bash\n /etc/init.d/postgresql start; ~/wait-for-postgres.sh ; su postgres -c \"psql -c \\\"create user activatm; alter user activatm with password 'activatm' \\\"\" ; chown -R elasticsearch:elasticsearch /elasticsearch_data; service elasticsearch start;  supervisord "  > run.sh

RUN chmod +x run.sh
# Run Supervisor - responsible to start up & keep alive all services:
# - ElasticSearch, Nginx, uWSGI, Celery, Redis
CMD ["./run.sh"]
 # ES port
EXPOSE 9200
# API port (via nginx)
EXPOSE 7979
# API documentation port (via nginx)
EXPOSE 7878

VOLUME $ELASTICTM_VOLUME
