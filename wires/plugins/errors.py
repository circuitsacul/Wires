import crescent

from wires import errors

from . import Plugin

plugin = Plugin()


@plugin.include
@crescent.catch_command(errors.WiresErr)
async def on_err(err: errors.WiresErr, ctx: crescent.Context) -> None:
    await ctx.respond(err.message, ephemeral=True)
