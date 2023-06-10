import flare
import hikari

from wires.database.models import TicketConfig

from .. import Plugin

plugin = Plugin()


async def create_ticket(config_id: int, user: int, username: str) -> str:
    config = await TicketConfig.exists(id=config_id)
    if config is None:
        return "This ticket configuration was deleted."

    thread = await plugin.app.rest.create_thread(
        config.channel,
        hikari.ChannelType.GUILD_PRIVATE_THREAD,
        username,
        invitable=False,
    )

    await plugin.app.rest.add_thread_member(thread, user)

    return f"Ticket created in <#{thread.id}>."


class CreateTicketButton(flare.Button):
    ticket_config_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        resp = await create_ticket(
            self.ticket_config_id, ctx.user.id, ctx.user.username
        )
        await ctx.respond(resp, flags=hikari.MessageFlag.EPHEMERAL)
