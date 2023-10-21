import contextvars

request_id: contextvars.ContextVar = contextvars.ContextVar("request_id")
