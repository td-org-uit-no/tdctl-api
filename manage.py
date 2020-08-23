#!/usr/bin/env python3

from app import create_app

app = create_app('production')

if __name__ == "__main__":
    app.run(host='0.0.0.0')
