#!/bin/bash
set -eux

echo 'This script assumes a setup using pipenv, gunicorn with systemd, and nginx.'
echo 'There are a number of steps involving sudo.'
echo 'User input is required at various stages.'

if ! command -v pipenv &> /dev/null
then
    echo "Please install pipenv first: https://pypi.org/project/pipenv/#installation"
    exit 1
fi

# Set domain
echo 'If you want to host abvdb on abvdb.domain.com, then your domain name is domain.com and your subdomain is abvdb'
read -p 'What is your domain name? (default: domain.com): ' ABVDB_DOMAIN
ABVDB_DOMAIN=${ABVDB_DOMAIN:-domain.com}
read -p 'What is your subdomain? (default: abvdb): ' ABVDB_SUBDOMAIN
ABVDB_SUBDOMAIN=${ABVDB_SUBDOMAIN:-abvdb}
ABVDB_URL=$ABVDB_SUBDOMAIN.$ABVDB_DOMAIN

# Pipenv
PROJECT_DIR=$(pwd)
pipenv install

# Create database
pipenv run python manage.py migrate

# Create secrets. This project uses django-environ and settings.py expects a .env file in the same directory as settings.py. See abvdb/.env.dist for an example.
DJANGO_SECRET_KEY=$(pipenv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

sed -E \
    -e "s!^DEBUG=.+$!DEBUG=False!" \
    -e "s!^SECRET_KEY=.+$!SECRET_KEY=$DJANGO_SECRET_KEY!" \
    .env.dist > .env

# This is a pretty redundant step considering the repo already has the static directory, but anyway.
pipenv run python manage.py collectstatic

# Create superuser
pipenv run python manage.py createsuperuser

# gunicorn
GUNICORN_BIN=$(pipenv run which gunicorn) # Because gunicorn is installed in a virtual environment, its path will be something like ~/.local/share/virtualenvs/abvdb-bCC_iaB8/bin/gunicorn rather than /bin/gunicorn.

## Optional: Test that gunicorn works at all by starting the server and loading the homepage. To bind to 0.0.0.0, modify ALLOWED_HOSTS in abvdb/settings.py first.
## $GUNICORN_BIN --daemon abvdb.wsgi:application --bind 127.0.0.1:8000
## curl 127.0.0.1:8000
## pkill -f gunicorn

WHOAMI=$(whoami)

echo 'gunicorn systemd config following docs: https://docs.gunicorn.org/en/stable/deploy.html'

read -p "Which user would you like to run gunicorn as? (default: $WHOAMI)" GUNICORN_USER
GUNICORN_USER=${GUNICORN_USER:-$WHOAMI}

read -p "Which group would you like to run gunicorn as? (default: $WHOAMI)" GUNICORN_GROUP
GUNICORN_GROUP=${GUNICORN_GROUP:-$WHOAMI}

echo 'Creating /var/{{log,run}/gunicorn and giving ownership to the specified user and group…'
sudo mkdir -pv /var/{log,run}/gunicorn/
sudo chown -cR $GUNICORN_USER:$GUNICORN_GROUP /var/{log,run}/gunicorn/

echo 'Creating your version of gunicorn.service.dist as gunicorn.service …'
sed -E \
    -e "s%^User=.+$%User=$GUNICORN_USER%" \
    -e "s%^Group=.+$%Group=$GUNICORN_GROUP%" \
    -e "s%^WorkingDirectory=.+$%WorkingDirectory=$PROJECT_DIR%" \
    -e "s%^ExecStart=.+$%ExecStart=$GUNICORN_BIN -c $PROJECT_DIR/config/gunicorn/prod.py%" \
    $PROJECT_DIR/config/gunicorn/gunicorn.service.dist > $PROJECT_DIR/config/gunicorn/gunicorn.service

NGINX_CONF_DEFAULT=/etc/nginx/nginx.conf
read -p "Where is nginx.conf? (default: $NGINX_CONF_DEFAULT): " NGINX_CONF
NGINX_CONF=${NGINX_CONF:-$NGINX_CONF_DEFAULT}

NGINX_USER=$(grep -E 'user\s+(.+);' $NGINX_CONF | awk '{print $2}' | sed -e 's/;//')
if [[ -n "$NGINX_USER" ]]; then
    echo "Could not find nginx user in $NGINX_CONF. Defaulting to www-data."
    NGINX_USER=www-data
fi

echo 'Creating your version of gunicorn.socket.dist as gunicorn.socket …'
echo 'This script assumes you want the gunicorn.socket SocketUser to be the nginx user.'
sed -E \
    -e "s%^SocketUser=.+$%SocketUser=$NGINX_USER%" \
    $PROJECT_DIR/config/gunicorn/gunicorn.socket.dist > $PROJECT_DIR/config/gunicorn/gunicorn.socket

echo 'Copying gunicorn.service and gunicorn.socket to /etc/systemd/system/ …'
sudo cp $PROJECT_DIR/config/gunicorn/gunicorn.service /etc/systemd/system/gunicorn.service
sudo cp $PROJECT_DIR/config/gunicorn/gunicorn.socket /etc/systemd/system/gunicorn.socket

echo 'Enabling gunicorn.socket …'
sudo systemctl enable --now gunicorn.socket

echo 'Testing systemd…it is ok if the returned HTML is an error 400.'
sudo -u www-data curl --unix-socket /run/gunicorn.sock http

# nginx
echo 'Creating your nginx config …'
sed -E \
    -e "s%abvdb.yourdomain.com;%$ABVDB_URL;%" \
    -e "s%alias /your/static/files/;%alias $PROJECT_DIR/static/;%" \
    $PROJECT_DIR/config/nginx/nginx.dist > $PROJECT_DIR/config/nginx/$ABVDB_URL

sudo cp $PROJECT_DIR/config/nginx/$ABVDB_URL /etc/nginx/sites-available/$ABVDB_URL
sudo ln -s /etc/nginx/sites-available/$ABVDB_URL /etc/nginx/sites-enabled/$ABVDB_URL

sudo nginx -t
sudo systemctl enable nginx.service
sudo systemctl start nginx
sudo systemctl reload nginx

echo 'Did this work?'
curl -L $ABVDB_URL

echo "Now change /etc/nginx/sites-available/$ABVDB_URL to support https, e.g. by using certbot."

if command -v certbot &> /dev/null; then
    while true; do
        read -p "Certbot exists on this system. Run certbot? (y/n): " CERTBOT_RUN
        case $CERTBOT_RUN in
            [yY]* ) echo 'Running certbot to enable https…';
                    sudo certbot -d $ABVDB_URL;;
            [nN]* ) echo 'https is important!';
                    break;;
        esac
    done
else
    echo "Certbot might be a good idea: this repo's nginx.dist file is not configured for https. See https://certbot.eff.org/."
fi
