from importlib.util import find_spec
import signal
import sys

if find_spec("docker") == None:
    raise SystemExit(
        f'ERROR (Missing dependency docker SDK): test script dependent on docker sdk for python \nrun pip install docker to install')

import docker
from docker.errors import APIError, NotFound

container_name = "mongodb_test"


def handle_container_running_or_name_conflict(client, container_name):
    container = client.containers.get(container_name)
    state = container.attrs['State']
    status = state['Status']
    if status == 'exited' or status == 'running':
        print(f'Detected existing container: Removing {container_name}')
        container.remove(v=True, force=True)


def run_mongodb_container(client, container_name):
    # starts up a mongodb container for test, must follow config setup in config.py
    return client.containers.run(
        image='mongo:latest',
        command="mongod --port 27018",
        network="docker_backend",
        name=container_name,
        detach=True,
        hostname="test_mongodb",
        auto_remove=True,
        remove=True
    )
# function to start up a container for running test
def start_mongodb_container(client):
    # handle error types
    responses = {
        409: handle_container_running_or_name_conflict
    }

    try:
        print(f'Starting {container_name}')
        return run_mongodb_container(client, container_name)
    except APIError as e:
        # does not handle errors in handle func
        responses[e.status_code](client, container_name)
    print(f'Starting {container_name}')
    # do not handle error here, want program to stop on error
    return run_mongodb_container(client, container_name)


def check_api_running(client):
    api_container_name = "tdctl_api"
    try:
        container = client.containers.get(api_container_name)
    except NotFound:
        raise SystemExit(
            f'ERROR(Could not find {container_name} container): API container must be running to perform tests')

    status = container.attrs['State']['Status']
    if status != "running":
        raise SystemExit(
            f'ERROR (container status : {status}): API container must be running to perform tests')
    return container


def setup_test_env(args):
    client = docker.from_env()
    api_container = check_api_running(client)
    mongodb_container = start_mongodb_container(client)
    # run pytest without description warnings
    _, stream = api_container.exec_run(f'pytest {" ".join(args)}', stream=True)
    for data in stream:
        print(data.decode(), end='')

    # with auto_remove, local volumes should be pruned on stop
    mongodb_container.stop()


def signal_handler(signum, frame):
    client = docker.from_env()
    print("\nSignal interrupt detected: Cleaning up container")
    try:
        container = client.containers.get(container_name)
        status = container.attrs['State']['Status']
        if status == "running":
            container.stop()
    except:
        # if any error, the container is not running and program can exit normally
        pass
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    setup_test_env(sys.argv[1:])
