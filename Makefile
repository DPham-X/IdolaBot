.PHONY: install-ubuntu
install-ubuntu:
	sudo apt-get update
	sudo apt-get -u upgrade
	sudo apt-get install -y python3 python3-dev build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -
	echo "PATH=$HOME/.poetry/bin:$PATH" >> ~/.bashrc
	source ~/.bashrc
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
