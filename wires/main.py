import asyncio
import sys

import crescent
import flare
import hikari

from wires.database import Database
from wires.model import Model

INTENTS = hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.MESSAGE_CONTENT


def run_app() -> None:
    model = Model()
    app = hikari.GatewayBot(model.config.token, intents=INTENTS)
    client = crescent.Client(app, model)

    flare.install(app)
    client.plugins.load_folder("wires.plugins")

    app.subscribe(hikari.StartingEvent, model.up)
    app.subscribe(hikari.StoppedEvent, model.down)

    app.run()


def create_migrations() -> None:
    db = Database()
    db.create_migrations(allow_empty=sys.argv[-1] == "--allow-empty")


def apply_migrations() -> None:
    model = Model()
    if model.config.database_url is None:
        raise ValueError("Can't apply migrations without DATABASE_URL")

    async def inner() -> None:
        await model.up()
        assert model._database
        await model._database.apply_migrations()
        await model.down()

    asyncio.run(inner())
