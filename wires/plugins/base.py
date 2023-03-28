import crescent

from . import Plugin

plugin = Plugin()


@plugin.include
@crescent.command(name="ping", description="Pong!")
async def ping(ctx: crescent.Context) -> None:
    latency = int(plugin.app.heartbeat_latency * 1_000)
    await ctx.respond(f"Pong! {latency}ms")
