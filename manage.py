#!/usr/bin/env python3
import uvicorn

from app import create_app


app = create_app()

if __name__ == "__main__":
    uvicorn.run('manage:app', host='0.0.0.0', port=5000,
                reload=True, log_level="info")
