.PHONY: start
start:
	# You need to set OPENAPI_API_KEY environment
	PYTHONPATH=. QA_SERVICE_LOG_LEVEL=DEBUG python app/main.py

.PHONY: clean
clean:
	# cleanup all saved index files
	find ./app/llama_index_server/saved_index -type f -exec rm {} +

.PHONY: test
test:
	make clean
	pytest app/tests
