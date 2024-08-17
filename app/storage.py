import ast
import dataclasses
import hashlib
import os
import pathlib

import duckdb
import openai
import pandas as pd
import pdftotext
import scipy

import settings

EMBEDDING_MODEL = settings.EMBEDDING_MODEL
OPENAI_API_KEY = settings.OPENAI_API_KEY
BATCH_SIZE = (
    settings.EMBEDDING_BATCH_SIZE
)  # you can submit up to 2048 embedding inputs per request


client = openai.OpenAI(api_key=OPENAI_API_KEY)


@dataclasses.dataclass
class FileMetadata:
    path: str
    content_hash: str


class EmbeddingsStorage:
    def __init__(self):
        self.db = duckdb.connect("file.db")
        self.db.sql(
            "CREATE TABLE IF NOT EXISTS files (id VARCHAR PRIMARY KEY, path TEXT, content TEXT)"
        )
        self.db.sql(
            "CREATE TABLE IF NOT EXISTS sections (doc_id VARCHAR REFERENCES files(id), n INTEGER, content TEXT, embeddings TEXT)"
        )

    def index_file(self, *, path: pathlib.Path):
        if not self._is_file_new(path):
            print("file already indexed, skipping")
            return

        file = self._load_file(path)
        self._split_into_sections(file)
        self._generate_embeddings(file=file)

    def find_string(self, query: str) -> tuple[list[str], list[float]]:
        df = self.db.sql("SELECT * FROM sections WHERE embeddings IS NOT NULL").df()

        df["embeddings"] = df["embeddings"].apply(ast.literal_eval)
        return self._strings_ranked_by_relatedness(query=query, df=df)

    # search function
    def _strings_ranked_by_relatedness(
        self,
        query: str,
        df: pd.DataFrame,
        relatedness_fn=lambda x, y: 1 - scipy.spatial.distance.cosine(x, y),
        top_n: int = 100,
    ) -> tuple[list[str], list[float]]:
        """Returns a list of strings and relatednesses, sorted from most related to least."""
        query_embedding_response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query,
        )
        query_embedding = query_embedding_response.data[0].embedding
        strings_and_relatednesses = [
            (row["content"], relatedness_fn(query_embedding, row["embeddings"]))
            for i, row in df.iterrows()
        ]
        strings_and_relatednesses.sort(key=lambda x: x[1], reverse=True)
        strings, relatednesses = zip(*strings_and_relatednesses)
        return strings[:top_n], relatednesses[:top_n]

    def _is_file_new(self, path: pathlib.Path) -> bool:
        with open(path, "rb") as f:
            pdf_pages = pdftotext.PDF(f)

        content = "\n\n".join(pdf_pages)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        response = self.db.sql(
            f"SELECT COUNT(*) FROM files WHERE id = '{content_hash}'"
        ).fetchall()
        if len(response) != 0:
            return False
        else:
            return True

    def _load_file(self, path: pathlib.Path) -> FileMetadata:
        with open(path, "rb") as f:
            pdf_pages = pdftotext.PDF(f)

        content = "\n\n".join(pdf_pages)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        insert_query = (
            f"INSERT INTO files VALUES ('{content_hash}', '{path}', $${content}$$)"
        )
        self.db.sql(insert_query)

        return FileMetadata(path=path, content_hash=content_hash)

    def _split_into_sections(self, file: FileMetadata):
        docs_df = self.db.sql(
            f"SELECT * FROM files WHERE id = '{file.content_hash}'"
        ).df()

        for _, doc in docs_df.iterrows():
            doc_id = doc["id"]
            sections = doc["content"].split("\n")
            # we are storing only paragraphs that have more then 30 letters.
            sections = [p for p in sections if len(p) > 30]

            for n, section in enumerate(sections):
                insert_query = (
                    f"INSERT INTO sections VALUES ('{doc_id}', {n},$${section}$$, NULL)"
                )
                self.db.sql(insert_query)

    def _generate_embeddings(self, file: FileMetadata):
        df = self.db.sql(
            f"SELECT * FROM sections WHERE doc_id = '{file.content_hash}' AND embeddings IS NULL"
        ).df()
        file_strings = df["content"].to_list()

        embeddings = []
        for batch_start in range(0, len(file_strings), BATCH_SIZE):
            batch_end = batch_start + BATCH_SIZE
            batch = file_strings[batch_start:batch_end]
            print(f"Batch {batch_start} to {batch_end-1}")
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
            for i, be in enumerate(response.data):
                assert (
                    i == be.index
                )  # double check embeddings are in same order as input
            batch_embeddings = [e.embedding for e in response.data]
            embeddings.extend(batch_embeddings)

        df["embeddings"] = embeddings

        for _, row in df.iterrows():
            insert_query = f"UPDATE sections SET embeddings = {row['embeddings']} \n WHERE sections.doc_id = $${row['doc_id']}$$ AND sections.n = {row['n']} "
            print(insert_query)
            self.db.sql(insert_query)
