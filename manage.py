#!/usr/bin/env python3
import sys
from app import create_app

def mainEntry(environment='development'):
    return create_app(environment)

# Gunicorn entry point generator
def appEntry():
    return mainEntry(environment='production')

if __name__ == "__main__":
    app = mainEntry()
    app.run(host='0.0.0.0')

