## This project contains backend logics of the traveler application

## technical stack:

FastAPI + llama index

## Development

- Setup Environment

```shell
cd llm-question-answering
virtualenv -p python3.9 env
source env/bin/activate
pip install -r requirements.txt
```

- Run the application locally

```shell
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

- api doc http://127.0.0.1:8080/docs

## Deploy

#### CI/CD(TODO)

need to execute the following cmds in linux environment, then upload function.zip to s3:
//wikivoyage-backend-fastapi/lambda/function.zip

```shell
cd env/lib/python3.9/site-packages
zip -r9 ../../../../function.zip .
cd ../../../../
zip -g ./function.zip -r app
```

## Test

#### integration test(for deployed apis)

- test the apis via postman, or from webpage https://uat.d31z7asgkhc1ua.amplifyapp.com/

#### test cases(for local tests)

- write test cases in /app/tests/test_*.py
- ensure `IS_LOCAL_TEST` environment variable is set in /app/tests/conftest.py. and then run
- need to pass local test cases before deploy.

```shell
pytest -ss
```
