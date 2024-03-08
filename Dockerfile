FROM python:3.9.18-alpine3.18
RUN sed -i s#dl-cdn.alpinelinux.org#mirrors.aliyun.com#g /etc/apk/repositories
RUN apk add --update --no-cache gcc g++ python3-dev musl-dev linux-headers make clang llvm-dev
WORKDIR /ai-bot
COPY ./requirements.txt /ai-bot/requirements.txt
RUN pip install --no-cache-dir -r /ai-bot/requirements.txt
COPY ./app /ai-bot/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
