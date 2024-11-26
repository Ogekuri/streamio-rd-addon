#!/bin/bash

# Imposta i valori di default
DEFAULT_PORT="44444"
DEFAULT_IP="0.0.0.0"

VENVDIR=".venv_run-python"

# Controlla se i parametri sono stati forniti
PORT=${1:-$DEFAULT_PORT}
IP=${2:-$DEFAULT_IP}

# Se non c'è il ${VENVDIR} lo crea
if ! [ -d "${VENVDIR}/" ]; then
    echo -n "Create virtual environment ..."
    mkdir ${VENVDIR}/
    virtualenv --python=python3.12 ${VENVDIR}/ >/dev/null
    echo "done."
fi

source ${VENVDIR}/bin/activate

echo "Run main:ap @"$IP":"$PORT" from "$(pwd -P)

echo -n "Install python requirements ..."
${VENVDIR}/bin/pip install -r requirements.txt >/dev/null
echo "done."

NODE_ENV=PRODUCTION ${VENVDIR}/bin/python -m uvicorn main:app --reload --host $IP --port $PORT

# termina il venv
deactivate

# cancella il virual environmenr (run-python.sh)
if [ -d "${VENVDIR}/" ]; then
    rm -rf ${VENVDIR}/
fi

# cancella le cache di sviluppo
find . -type d -iname "__pycache__" -exec rm -rf "{}" +
