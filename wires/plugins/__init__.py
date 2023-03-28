import typing as t

import crescent
import hikari

if t.TYPE_CHECKING:
    from wires.model import Model  # noqa: F401

Plugin = crescent.Plugin[hikari.GatewayBot, "Model"]
