import pathlib
import random
import time

import openai
import pandas as pd
import tiktoken

import settings
import storage

GPT_MODEL = settings.GPT_MODEL
OPENAI_API_KEY = settings.OPENAI_API_KEY


client = openai.OpenAI(api_key=OPENAI_API_KEY)


def num_tokens(text: str, model: str = settings.GPT_MODEL) -> int:
    """Return the number of tokens in a string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


class API:
    def __init__(self):
        self.uploads_dir = pathlib.Path("uploads")
        self.uploads_dir.mkdir(exist_ok=True)
        self.storage = storage.EmbeddingsStorage()

    def upload_file(self, *, filename: str, data: bytes):
        file_path = self.uploads_dir / filename
        with open(file_path, "wb") as f:
            f.write(data)
        self.storage.index_file(path=file_path)

    def ask_file(self, *, prompt: str, token_budget: int = 4096 - 500):
        """Answers a query using GPT and a dataframe of relevant texts and embeddings."""
        message = self.query_message(prompt, token_budget=token_budget)

        messages = [
            {"role": "system", "content": "You answer questions the paper bellow."},
            {"role": "user", "content": message},
        ]
        response = client.chat.completions.create(
            model=GPT_MODEL, messages=messages, temperature=0, stream=True
        )
        for chunk in response:
            chunk_content = chunk.choices[0].delta.content
            if chunk_content is not None:
                yield chunk_content

    def query_message(self, query: str, token_budget: int) -> str:
        """Return a message for GPT, with relevant source texts pulled from a dataframe."""
        strings, _ = self.storage.find_string(query)
        introduction = 'Use the below articles to answer the subsequent question. If the answer cannot be found in the articles, write "I could not find an answer."'
        question = f"\n\nQuestion: {query}"
        message = introduction
        for string in strings:
            next_article = f'quote from paper:\n\n"{string}\n"'
            if (
                num_tokens(message + next_article + question, model=GPT_MODEL)
                > token_budget
            ):
                break
            else:
                message += next_article
        return message + question
