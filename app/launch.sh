#!/bin/bash

# start backend index server
python ./llama-index/index_server.py &
echo "index_server running..."

# wait for the server to start - if creating a brand new huge index, on startup, increase this further
sleep 10

# start the fastapi server
# todo
#python main.py &
#echo "fastapi running..."