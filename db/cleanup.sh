#!/usr/bin/env bash
cd db_data && 
    find . ! -name '.gitignore' -type f -exec rm -f {} + && 
    find . ! -name '.' -type d -exec rm -rf {} + && 
    cd ..
