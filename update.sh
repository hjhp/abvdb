#!/bin/bash
git pull
pipenv run python manage.py migrate
pipenv run python manage.py collectstatic
pkill -HUP gunicorn
