import os
import typing as t
from dataclasses import dataclass

import dotenv

from wires.utils import unwrap


@dataclass
class Config:
    token: str
    database_url: str | None = None

    @classmethod
    def load(cls) -> t.Self:
        dotenv.load_dotenv()
        return cls(
            token=unwrap(os.getenv("TOKEN"), "no token"),
            database_url=os.getenv("DATABASE_URL"),
        )
