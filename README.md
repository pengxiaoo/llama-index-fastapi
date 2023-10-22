## technical stack:

FastAPI + llama index

## Development

- Setup Environment

```shell
virtualenv -p python3.9 env
source env/bin/activate
pip install -r requirements.txt
```

- Run the application locally

```shell
uvicorn app.main:app --host 127.0.0.1 --port 8081 --reload
```

- api doc http://127.0.0.1:8081/docs

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

#### test cases(for local tests)

- write test cases in /app/tests/test_*.py
- ensure `IS_LOCAL_TEST` environment variable is set in /app/tests/conftest.py. and then run
- need to pass local test cases before deploy.

```shell
pytest -ss
```
