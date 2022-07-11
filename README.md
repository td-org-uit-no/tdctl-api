
# tdctl-api
> Application Programming Interface for TDCTL


## Installation
### 1. Clone this repository by running:
  * ```git clone https://github.com/td-org-uit-no/tdctl-api.git```

### 2. Launching locally
  * To run the API locally use the `manage.py` script, which will run a local instance of the API:  ```./manage.py``` 
  * The HTTP server should by default be run on [localhost:5000](http://localhost:5000/)
  * Please note that datasources(or equivalent mockup code) used by the API must be available for all functionality to work.

## Tests :heavy_check_mark:
The test are running on a test client who resets after every test. To create data available over multiple tests insert the seeding in the client instance in `conftest.py`
### Running tests
:information_source: Make sure the mongodb server is running. To start the mongo server  run `mongod -f db.yml` in the db folder
  * To run the tests run the following command `pytest -rx`
  * To run a specific test: `pytest -rx <path to test file>`
