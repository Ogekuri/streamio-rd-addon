#!/bin/bash

# cancella il virtual environment
VENVDIR=".venv"
if [ -d "${VENVDIR}/" ]; then
    rm -rf ${VENVDIR}/
fi

# cancella il virual environmenr (run-python.sh)
VENVDIR=".venv_run-python"
if [ -d "${VENVDIR}/" ]; then
    rm -rf ${VENVDIR}/
fi

# cancella le cache di sviluppo
find . -type d -iname "__pycache__" -exec rm -rf "{}" +



# Build and run container
sudo docker compose up --build

# Remove container after Ctr+C

# TEST
ID=$(sudo docker ps -a | grep "streamio-rd-addon-test" | awk '{print $1}')
if [ -n "$ID" ]; then
    sudo docker rm -f $ID >/dev/null
fi
ID=$(sudo docker images -a | grep "streamio-rd-addon-test" | awk '{print $3}')
if [ -n "$ID" ]; then
    sudo docker rmi $ID >/dev/null
fi

# PRODUCTION
ID=$(sudo docker ps -a | grep "streamio-rd-addon-production" | awk '{print $1}')
if [ -n "$ID" ]; then
    sudo docker rm -f $ID >/dev/null
fi


ID=$(sudo docker images -a | grep "streamio-rd-addon-production" | awk '{print $3}')
if [ -n "$ID" ]; then
    sudo docker rmi $ID >/dev/null
fi

# Print remaining containers and images
#echo "Docker containers:"
#sudo docker ps -a

#echo "Docker images:"
#sudo docker images -a
