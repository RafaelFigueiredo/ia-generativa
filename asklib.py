import pathlib
import random
import time


class API:
    def __init__(self):
        self.uploads_dir = pathlib.Path("uploads")
        self.uploads_dir.mkdir(exist_ok=True)

    def upload_file(self, *, filename: str, data: bytes):
        with open(self.uploads_dir / filename, "wb") as f:
            f.write(data)

    def ask_file(self, *, prompt: str):
        response = random.choice(
            [
                "Hello there! How can I assist you today?",
                "Hi, human! Is there anything I can help you with?",
                "Do you need help?",
            ]
        )
        for word in response.split():
            yield word + " "
            time.sleep(0.05)
