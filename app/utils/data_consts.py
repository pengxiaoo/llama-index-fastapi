import os

EXPECTED_USERNAME = os.environ.get("AI_BOT_ADMIN_USERNAME", "admin")
EXPECTED_PASSWORD = os.environ.get("AI_BOT__ADMIN_PASSWORD", "123456")
MONGO_URI = os.environ.get("AI_BOT_MONGO_URI", "mongodb://localhost:27017")
DOCUMENT_META_LIMIT = os.environ.get("AI_BOT_DOCUMENT_META_LIMIT", 10000)
