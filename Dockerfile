FROM python:3.9.18-slim
WORKDIR /ai-bot
COPY ./requirements.txt /ai-bot/requirements.txt
RUN pip install --no-cache-dir -r /ai-bot/requirements.txt
COPY ./app /ai-bot/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
