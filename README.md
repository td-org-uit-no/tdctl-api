
# tdctl-api
> Application Programming Interface for TDCTL


## Contributing
### 1. Clone this repository by running:
  * ```git clone https://github.com/td-org-uit-no/tdctl-api.git```

### 2. Development environment
You can either start up both the backend and mongodb locally, or you can run them in separate docker containers using docker-compose.

**NB: Doing both may result in issues since docker and mongod will in some cases use different users for writing to the volume folder `db_data`. If this happen, you should either try to fix the permissions of the folder, or you can delete and recreate it**

#### 2.1 Pipenv
   * To run the API and install the required dependencies using pipenv:
     1. [install pipenv](https://pipenv.pypa.io/en/latest/install/)
     1. run `pipenv install` to install all dependencies into the pipenv virtuall enviroment
     2. run `pipenv shell` to enter the virtuall enviroment with all dependencies installed
  * To run the API locally use the `manage.py` script, which will run a local instance of the API:  ```./manage.py``` 
  * To run mongodb locally you must be inside the db folder, and then run `mongod -f db.yml`. `db.yml` uses relative paths, and the relative paths are relative from where you run the command from and not from the file itself.
  * The HTTP server should by default be run on [localhost:5000](http://localhost:5000/)
  * Please note that datasources(or equivalent mockup code) used by the API must be available for all functionality to work.

#### 2.2 Docker
  * To use docker, you can run: 
    1. `docker-compose -f .docker/docker-compose.development.yml build`
    2. `docker-compose -f .docker/docker-compose.development.yml up`
    * This will launch both the backend and mongodb inside two separate containers.
  * To see output from the backend while working, you can use `docker logs tdctl_api -f`

## 3.Testing :heavy_check_mark:
The test are running on a test client who resets after every test. To create data available over multiple tests insert the seeding in the client instance in `conftest.py`
### 3.1 Running tests
**:information_source: Make sure the mongodb server is running. To start the mongo server run `mongod -f db.yml` in the db folder**
  * To run all tests: `pytest -rx`
  * To run a specific test: `pytest -rx <path to test file>`

See [pytest documentation](https://docs.pytest.org/en/7.2.x/) for more information
### 3.2 Running tests in docker
**To perfore tests when using docker, run the `pytest_docker.py` file from your shell and the script will execute the tests in the running container.**

The script will pass all flags into the container, so it can be used in the same way as pytest i.e <br> 
`python3 pytest_docker.py -s` will be the same as running `pytest -s`

  - **Requirements:**
    - tdctl_api container must be running
    - Docker SDK for python must be installed `pip install docker`

