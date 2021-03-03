#
# Typically there are only two commands you will be using on a regular basis
# make down - stop any running containers
# make prod_containers - builds containers and runs them
#



all: 
	docker-compose -f docker-compose.prod.yml up -d --build



just_docker: 
	docker build .

down:
	docker-compose -f docker-compose.prod.yml down --remove-orphans

shell:
	docker container exec -it memo_memo_monitor_1 /bin/bash