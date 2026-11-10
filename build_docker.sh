#!/bin/sh

sudo docker build --no-cache -t videopoker-api -f api-server/Dockerfile .
sudo docker run -p 8001:8001 videopoker-api
