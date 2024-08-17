from dotenv import load_dotenv

load_dotenv()

import os

EMBEDDING_BATCH_SIZE = 1000
EMBEDDING_MODEL = "text-embedding-3-small"
GPT_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


#https://platform.openai.com/docs/guides/embeddings
EMBEDDING_SIZE = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072
}[EMBEDDING_MODEL]