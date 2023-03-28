import logging

from wires import errors
from wires.config import Config
from wires.database import Database

LOG = logging.getLogger(__name__)


class Model:
    def __init__(self) -> None:
        self.config = Config.load()
        self._database: Database | None = None

    @property
    def database(self) -> Database:
        if not self._database:
            raise errors.NoDatabase

        return self._database

    async def up(self, *_: object) -> None:
        if not self.config.database_url:
            LOG.warning("Running bot in no-database mode.")
            return

        self._database = Database()
        await self._database.connect(dsn=self.config.database_url)

    async def down(self, *_: object) -> None:
        if self._database:
            await self._database.cleanup()
