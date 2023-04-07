#!/bin/bash

docker_command=""
path=".docker/docker-compose.development.yml"
utils_path=utils

check_compose_version() {
    compose_command="docker compose"
    if ! command -v ${compose_command} &> /dev/null; then
        # can't find docker compose, tries older version
        compose_command="docker-compose"
        if ! command -v $compose_command &> /dev/null; then
            # couldn't find docker-compose i.e no version of docker compose is installed
            return
        fi
    fi
    docker_command="$compose_command -f"
}

usage() {
    echo "Utils script for docker commands in development: 
Required:
    compose:
        passes the command line arguments to '${docker_command} ${path} {provided arguments}'.
$(exec_usage)
    seed:
        seeds database using the seeding file
    test:
        runs the docker test file, and sends any additional arguments to the pytest command
            - 'seed -s' will be the same as 'pytest -s'
"
}

exec_usage() {
    echo "    exec:
        interactive shell for development containers (api or db)
        Options:
            api - interactive shell for api container (default)
            db - interactive monogsh shell for db 
"
}

run_compose() {
    $docker_command $path $@
}

exec_api() {
    docker exec -it tdctl_api bash
}

exec_db() {
    container=mongodb_dev
    host=td_mongodb
    port=26900
    docker exec -it $container mongosh --host $host --port $port
}

interactive_shell() {
    if [ $# = 0 ];then
        # tdctl api is default exec container
        exec_api
        exit 1
    fi
    case $1 in 
        api) shift; exec_api;;
        db) shift; exec_db;;
        -h | --help) shift; exec_usage;;
        * ) exec_usage;;
    esac
}

seed_db() {
    # runs seeding as module (fixes imports)
    docker exec tdctl_api python3 -m $utils_path.seeding
}

run_tests() {
    test_file=pytest_docker.py
    python3 $utils_path/$test_file $@
}

parse_arguments() {
    if [ $# = 0 ];then
        usage
        exit 1
    fi
    # couldn't find docker compose or docker-compose
    if [ -z "$docker_command" ];then
        echo "Could not find any versions of (docker compose or docker-compose)"
        exit 1
    fi

    case $1 in 
        compose) shift; run_compose $@;;
        exec) shift; interactive_shell $@;;
        seed) shift; seed_db;;
        test) shift; run_tests $@;;
        -h | --help) shift; usage;;
        * ) usage;;
    esac
}

check_compose_version
parse_arguments $@
