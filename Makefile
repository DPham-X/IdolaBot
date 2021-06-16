.PHONY: install-ubuntu
install-ubuntu:
	sudo apt-get update
	sudo apt-get -u upgrade
	sudo apt-get install -y python3 python3-dev build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev	git submodule update --init --recursive
	make install

.PHONY: install
install:
	poetry install
	git submodule update --init --recursive

.PHONY: format
format:
	poetry run black idola
	poetry run isort idola

.PHONY: update
update:
	git pull
	git submodule update --recursive --remote

.PHONY: start
start:
	./start_bot.sh

.PHONY: stop
stop:
	./stop_bot.sh
