# Parallel CI agnostic python testing in Github Actions

## Introdicution to existing environment

At a work project we are using docker-compose to raise dev environment

```yaml
version: '3.8'
services:
  db:
    image: postgres:13
    environment:
      POSTGRES_HOST_AUTH_METHOD: trust
      POSTGRES_DB: default
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    expose:
      - "5432"

  redis:
    image: redis
    expose:
      - "6379"

  app:
    environment:
      SOME_ENV_VAR: '123'
    links:
      - db
      - redis
    build: .
```

we have around 5000 unit and integration tests in a Django project, which we test with pytest. All of them are run pretty much runnable with command like this one in GIthub Actions:

```bash
docker-compose run -v $(pwd):/code -u 0 app pytest --cov=. --junit-xml=unit.xml .
```

The main advantages of this approach

- in having same tests runnable locally,
- same side car dependencies raised in CI, same test environment in local dev env and CI environment ran.
- The code for this CI test run is easily transferable to any other CI tool.

As disadvantages:

- people need to ensure for CI runner to have `docker-compose` available inside CI job, with docker daemon provided.
- And potentially side car containers can be not fast enough raising themselves. In this case you would wish to apply tool like [wait_for_it.sh](https://github.com/vishnubob/wait-for-it), which without any other dependencies will wait necessary time for dependency being available (`wait_for_it.sh db:5432 -t 60 && wait_for_it.sh redis:5379 -t 60 && pytest` in our case for example)

**Important note**

As artifacts of a test run, we produce `unit.xml`, and `coverage.xml` files, to ensure having published passed tests into Github Actions graphical interface, and coverage results. It allows faster seeing logs to specific broken tests without digging through raw log output.

```yaml
      - name: Publish Unit Test Results
        uses: EnricoMi/publish-unit-test-result-action@v1
        if: always()
        continue-on-error: true
        with:
          files: unit.xml
          check_name: Pytest tests
      - name: Display coverage
        if: always()
        continue-on-error: true
        uses: ewjoachim/coverage-comment-action@v1
        with:
          GITHUB_TOKEN: ${{ github.token }}
          COVERAGE_FILE: coverage.xml
```

![](assets/passed_GUI_tests.png)

## Task definition

Usually people assume to use to use (pytest-xdist)[https://pypi.org/project/pytest-xdist/] in python ecosystem in order to have tests runable in parallel. I was offered to collect flappy tests data in datadog, and after having them analyzed to fix them so that nothing would prevent their running in pytest-xdist. We needed to run our CI tests faster :)

## Analysis

First collected broken tests had wrongly working Django translation, which is depended on linux Gettext. According to (found information)[https://www.gnu.org/software/gettext/manual/gettext.html] - gettext is not really

> The GNU Gettext runtime supports only one locale per process. It is not thread-safe to use multiple locales and encodings in the same process. This is perfectly fine for applications that interact directly with a single user like most GUI applications, but is problematic for services and servers.

After having found an interesting source of information [at this page](https://stackoverflow.com/questions/45733763/pytest-run-tests-parallel), we can assume that default method to run pytest uses multithreading, but multiprocessing is clearly possible as well. (See code below). It can fix part of test problems at least.

```bash
pip install pytest-xdist

# The most primitive case, sending tests to multiple CPUs:
pytest -n NUM

# Execute tests within 3 subprocesses.
pytest --dist=each --tx 3*popen//python=python3.6

# Execute tests in 3 forked subprocess. Won't work on windows.
pytest --dist=each --tx 3*popen//python=python3.6 --boxed

# Sending tests to the ssh slaves
pytest --dist=each --tx ssh=first_slave --tx ssh=seconds_slave --rsyncdir package package

# Sending tests to the socket server, link is available below.
python socketserver.py :8889 &
python socketserver.py :8890 &
pytest --dist=each --tx socket=localhost:8889 --tx socket=localhost:8890
```

Further collecting data from datadog, there were tests broken because tests used cache in shared storage `redis`
Another tests became broken because during count of SQL requests made by ORM, it made more than necessary, because another process was running query to db too. Which allowed making conclusion that having shared side car container `db`, made tests broken just because they use same db instance.

It became obvious, that despite recommendations to fix caching using in memory solution, we would be encountering one or another new reasons why tests are broken again and again.

It allows us to make next conclusion, that if we are using pytest-xdist:

- It is additional development cost to fix all current parallel problems in tests, and it will increase development cost in a future to keep it that way
- we would be decreasing how good our test environment is, with replacing side car container like Redis with in memory alternatives, which will decrease quality of tests.

## Solution

Instead of using pytest-xdist... I realized just to split pytest tests into groups. Luckily there is even library for this - (pytest-split)[https://pypi.org/project/pytest-split/]. Each group of tests we will be running in its own raised docker-compose group of containers, each process would be having its own db instance, redis instance and whatever else side car dependency needed. Thus, it would be perfect imitation for tests being run still in sequence instead of being run in parallel :) The only little problem we need to solve after that, with having merged coverage and junit output results for out Github Actions GUI.

Since we are in Python, the solution is implemented in python as well, with the help of `subprocess` library for multiprocessing and `argparse` library to have better self documented interface.

##### 1. Github Actions Self hosted runner

Firstly we raise self hosted Github Actions runner with available docker-compose inside. Since Github Actions installing documentation is offering only installation to baremetal Linux and clearly lacking in this regard in comparison to Gitlab CI which offers its runnes installations ready solutions for docker and even kubernetes, we write our own solution to automate default Github Actions installation through `pyexpect` library, and thus having it container compatible as well. Command to run GA runner becomes `TOKEN=your_github_token_to_register_runner docker-compose up`. See full code in [repository](https://github.com/darklab8/darklab_github_ci) for reference.

* Cloning to some machine with installed docker and docker-compose https://github.com/darklab8/darklab_github_ci
* TOKEN=your_github_token_to_register_runner docker-compose up

##### 2. Triggering CI

* Just pushing any code to master or opening pull request to merge commits to master :) You see full code of [a solution here](https://github.com/darklab8/darklab_article_parallel_pytest)

##### Debugging tips

python3 -m make parallel_pytest --dry # can help you to run commands only without running them
or just run tests with less amount of selected tests.
