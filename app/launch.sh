#!/bin/bash

# start backend index server
python ./llama-index/index_server.py &
echo "index_server running..."

# wait for the server to start - if creating a brand new huge index, on startup, increase this further
sleep 10

# start the fastapi server
# TODO 在这里启动fastapi，这样的话直接运行launch.sh就可以同时启动index_server和fastapi
#python main.py &
#echo "fastapi running..."