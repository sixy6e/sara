# SARA - docker installation

Complete build of SARA application through docker installation for test purpose

## Building docker file
	
Building the docker file should be done once. It supposes that you have [docker](https://www.docker.com/docker.io) installed on your system 

	export SARA_SRC=/Users/jrom/Devel/sara
	cd ${SARA_SRC}/docker
	docker build -t sara --force-rm .

## Install and test SARA

### Install SARA within docker image

First launch sara image

	export SARA_SRC=/Users/jrom/Devel/sara
	docker run -v ${SARA_SRC}:/sara --rm -ti sara /bin/bash

Within the docker image, launch the following

	export SARA_HOME=/sara
	cd $SARA_HOME

	# Initialize database
	service postgresql-9.5 initdb

	# Local connection to db without password
	cat <<EOF > /var/lib/pgsql/9.5/data/pg_hba.conf
	local   all             all                                     trust
	host    all             all             127.0.0.1/32            trust
	host    all             all             ::1/128                 trust
	EOF

	# Start postgres service
	service postgresql-9.5 start
	
