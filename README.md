<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/td-org-uit-no/graphics/9fa70bc36f3d47e23f0961fe9dd5f1d0675db5a2/logo/logo-with-tagline/td-dark-tagline.svg">
  <img width="100%" height="100%" alt="TD logo" src="https://github.com/td-org-uit-no/graphics/blob/master/logo/logo-with-tagline/td-light-tagline.svg" ali>
</picture>

# Website API

Welcome to the TD API project! This open-source project provides a flexible and easy-to-use interface for accessing and managing data related to TD. With this API, you can access a variety of information, including events, news, resources, and more. We believe in the power of open-source software and welcome contributions from developers of all skill levels. Join us in building a better future for TD!

This is the repository for the backend of our website. So if you want to contribute to our frontend, please look at this [repository](https://github.com/td-org-uit-no/tdctl-frontend) instead.



## Tech Stack

We have chosen a tech stack that should make it easy for new students to quickly learn the ropes and start contributing.

**API:** Docker, Python, Fast API, MongoDB


## Run Locally
> We prefer a containerized development. Therefore, the only dependeciy needed to work on this project is [docker/ docker-compose](https://docs.docker.com/get-docker/). To make this easier for new developers we have created a script that can be  used to run the api in a container locally, this script is placed in the project root and is called ```dev_utils.sh```.

1. Clone the project

```bash
    git clone git@github.com:td-org-uit-no/tdctl-api.git
```
2. Go to the project directory

```bash
    cd tdctl-api
```

3. Add executable rights to the container util script
```bash
    chmod +x ./dev_utils.sh
```

4. Build docker container
> This is only needed if it is the first time you running the server or if there has been any changes to the runtime environment of the server. 
```bash
    ./dev_utils.sh compose build
```

5. Launch the container
    * Run container in background
        > Shutdown the container by running ```./dev_utils.sh compose down```
        ```bash
            ./dev_utils.sh compose up -d
        ```
        - You can now start a interactive shell within the container by running the command
            > To get an interactive shell in the database container add ```db``` to the end of this command
            ```bash
                ./dev_utils.sh exec
            ```
    * Run the container and view container output
        > Shutdown the container by pressing ```ctrl-C```
        ```bash
            ./dev_utils.sh compose up
        ```
6. **Optional:** Seed the database with test users:
    > This will provide you with a dummy admin user which has the credentials *Username* : ```Admin``` *Password* : ```Admin!234```
    ```bash
        ./dev_utils.sh seed
    ```

When the container is up and running you should be to view the api at [localhost:5000](http://localhost:5000)
    
        
## Running Tests

To run tests make sure the container is running, then run the following command

```bash
  ./dev_utils.sh test
```

You should now se an output similar to this:
```
Starting mongodb_test
============================= test session starts ==============================
platform linux -- Python 3.9.16, pytest-7.3.0, pluggy-1.0.0
rootdir: /app
plugins: anyio-3.6.2
collected 46 items

tests/test_decorator.py ...                                              [  6%]
tests/test_endpoints/test_admin.py .....                                 [ 17%]
tests/test_endpoints/test_auth.py ...                                    [ 23%]
tests/test_endpoints/test_event.py .....................                 [ 69%]
tests/test_endpoints/test_jobs.py ....                                   [ 78%]
tests/test_endpoints/test_mail.py .                                      [ 80%]
tests/test_endpoints/test_members.py .......                             [ 95%]
tests/test_validation/test_file_validation.py .                          [ 97%]
tests/test_validation/test_password_validation.py .                      [100%]

============================= 46 passed in 25.71s ==============================
```
## Missing Features?

Feel free to add issues to our [issue tracker](https://github.com/td-org-uit-no/tdctl-frontend/issues), or create your own  [pull request](#Contributing).
## Contributing

Contributions are always welcome!

See [`contributing.md`](./CONTRIBUTING.md) for ways to get started.

## Support

For support, email nettside-ansvarlig@td-uit.no

