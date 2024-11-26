#!/bin/bash

cd -- "$(dirname "$0")"
echo "Run on path: "$(pwd -P)

source .venv/bin/activate

/usr/bin/env .venv/bin/python search/plugins/test_plugins.py
