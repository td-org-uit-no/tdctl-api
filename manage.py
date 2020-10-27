#!/usr/bin/env python3
import uvicorn

from app import create_app


def productionApp():
    return create_app("production")


development = create_app("development")

if __name__ == "__main__":
    uvicorn.run('manage:development', host='0.0.0.0',
                reload=True, log_level="info")
