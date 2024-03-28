import os

EXPECTED_USERNAME = os.environ.get("AI_BOT_ADMIN_USERNAME", "your-username")
EXPECTED_PASSWORD = os.environ.get("AI_BOT_ADMIN_PASSWORD", "your-password")
MONGO_URI = os.environ.get("AI_BOT_MONGO_URI", "mongodb://localhost:27017")
DOCUMENT_META_LIMIT = os.environ.get("AI_BOT_DOCUMENT_META_LIMIT", 10000)
API_TIMEOUT = 10
