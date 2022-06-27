# incitev
## This repository is dedicated to the implementation of EMS.

# Brocker

### following instruction for running a mosquitto broker in docker container

configuration file in `/mirtaheri/mosquitto/conf/mosquitt.conf` includes:

`
\n persistence true
\n persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log

listener 1883
## Authentication ##
allow_anonymous true
#allow_anonymous false
`
password_file /mosquitto/conf/mosquitto.conf


`docker run -d --restart unless-stopped -p 1882:1883 -v /home/mirtaheri/mosquitto/conf/mosquitto.conf:/mosquitto/config/mosquitto.conf eclipse-mosquitto`
