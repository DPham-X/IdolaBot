# Discord Bot for IDOLA

## Installation

    git clone https://github.com/iXyk/IdolaBot.git
    cd IdolaBot
    git submodule update --init --recursive

### Ubuntu 20.04

    cd ..

Ensure apt is updated

    sudo apt-get update
    sudo apt-get -y upgrade

Ensure that python3 virtualenv is installed

    sudo apt-get install -y python3-virtualenv

Create the idola virtualenv, activate it and install the python dependencies

    python3 -m virtualenv -p python3 idola-venv
    source idola-venv/bin/activate
    cd IdolaBot

    pip install -r requirements.txt

To install the optional levenshtein package

    sudo apt-get install -y python3 python3-dev build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev
    pip install -r requirements-optional.txt

Next fill out the idola environment variables (`.env`) located inside `IdolaBot/.env`

Once the environment variables have been filled out run that start script

    ./start_bot.sh

## Updating

    git pull https://github.com/iXyk/IdolaBot.git

    git submodule update --recursive --remote
