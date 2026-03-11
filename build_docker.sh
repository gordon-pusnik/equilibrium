#!/bin/sh

sudo docker build --no-cache -t videopoker-api -f api-server/Dockerfile .
sudo docker run -p 8000:8000 videopoker-api
