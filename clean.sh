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
