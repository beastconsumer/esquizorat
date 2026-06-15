#!/bin/bash

# Iniciar Web API em background
gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 web_api:app &

# Iniciar Central Server
gunicorn --bind 0.0.0.0:5001 --workers 2 --threads 4 central_server:app
