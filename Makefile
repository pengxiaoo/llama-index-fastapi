.PHONY: start
start:
	# You need to set OPENAPI_API_KEY environment
	PYTHONPATH=. python app/main.py

.PHONY: clean
clean:
	# cleanup all saved index files
	find ./app/llama_index_server/saved_index -type f -exec rm {} +

.PHONY: test
test:
	make clean
	pytest app/tests
