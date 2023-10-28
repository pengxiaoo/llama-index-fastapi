## technical stack:

FastAPI + llama index

### reference:

- [llama index official demo doc: fullstack_app_guide](https://docs.llamaindex.ai/en/stable/understanding/putting_it_all_together/apps/fullstack_app_guide.html)
- [llama index official demo code: flask_react](https://github.com/logan-markewich/llama_index_starter_pack/tree/main/flask_react)

## Development

- Setup Environment

```shell
virtualenv -p python3.9 env
source env/bin/activate
pip install -r requirements.txt
```

- Run the application locally

```shell
PYTHONPATH=. python app/launch.py
```

- api doc http://127.0.0.1:8081/docs

## Deploy

#### CI/CD(TODO)

## Test

#### test cases(for local tests)

- write test cases in /app/tests/test_*.py
- need to pass local test cases before deploy.

```shell
pytest -ss
```
