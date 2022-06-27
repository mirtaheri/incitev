# incitev
## This repository is dedicated to the implementation of EMS.

# Brocker

### following instruction for running a mosquitto broker in docker container

configuration file in `/mirtaheri/mosquitto/conf/mosquitt.conf` includes:

`
<br>
`persistence true`
<br>
`persistence_location /mosquitto/data/`
<br>
`log_dest file /mosquitto/log/mosquitto.log`
<br>
`listener 1883`
<br>
## Authentication ##
<br>`allow_anonymous true`
<br>#`allow_anonymous false`


password_file /mosquitto/conf/mosquitto.conf


`docker run -d --restart unless-stopped -p 1882:1883 -v /home/mirtaheri/mosquitto/conf/mosquitto.conf:/mosquitto/config/mosquitto.conf eclipse-mosquitto`
