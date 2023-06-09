import asyncpg
import crescent
import hikari

from wires import constants
from wires.database.models import TicketConfig
from wires.errors import WiresErr

from .. import Plugin

plugin = Plugin()
group = crescent.Group(
    "tickets",
    "Manage ticket configurations.",
    default_member_permissions=hikari.Permissions.MANAGE_GUILD,
    dm_enabled=False,
)


async def ticket_config_autocomplete(
    ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    assert ctx.guild_id
    configs = await TicketConfig.fetchmany(guild_id=ctx.guild_id)
    return [
        hikari.CommandChoice(name=config.name, value=config.name) for config in configs
    ]


@plugin.include
@group.child
@crescent.command(name="list", description="List existing ticket configurations.")
class ListTicketConfigs:
    async def callback(self, ctx: crescent.Context) -> None:
        assert ctx.guild_id
        configs = await TicketConfig.fetchmany(guild_id=ctx.guild_id)

        if not len(configs):
            raise WiresErr("There are no existing ticket configurations.")

        embed = hikari.Embed(color=constants.EMBED_DARK_BG)
        for config in configs:
            embed.add_field(config.name, f"<#{config.channel}>", inline=True)

        await ctx.respond(embed=embed)


@plugin.include
@group.child
@crescent.command(name="new", description="Create a new ticket configuration.")
class NewTicketConfig:
    channel = crescent.option(
        hikari.TextableGuildChannel, "The channel to open ticket threads in."
    )
    name = crescent.option(
        str, "The name of the ticket configuration.", max_length=32, min_length=2
    )

    async def callback(self, ctx: crescent.Context) -> None:
        assert ctx.guild_id

        name = "".join([c for c in self.name if c.isalnum() or c == "_"])
        name_len = len(name)
        if name_len < 2 or name_len > 32:
            raise WiresErr(
                "`name` must be between 2 and 32 characters, and only consist of "
                "a-zA-Z0-9_."
            )

        try:
            await TicketConfig(
                name=name, channel=self.channel.id, guild_id=ctx.guild_id
            ).create()
        except asyncpg.UniqueViolationError:
            raise WiresErr("The name of a ticket configuration must be unique.")

        await ctx.respond(
            f"Created config '{name}'. Use `/tickets entrypoint` to send an entrypoint "
            "message."
        )


@plugin.include
@group.child
@crescent.command(name="delete", description="Delete a ticket configuration.")
class DeleteTicketConfiguration:
    name = crescent.option(
        str,
        "The name of the ticket configuration.",
        autocomplete=ticket_config_autocomplete,
    )

    async def callback(self, ctx: crescent.Context) -> None:
        assert ctx.guild_id
        config = (
            await TicketConfig.delete_query()
            .where(guild_id=ctx.guild_id, name=self.name)
            .execute()
        )
        if not len(config):
            raise WiresErr(f"No ticket configuration named '{self.name}' exists.")
        await ctx.respond(f"Deleted ticket configuration '{self.name}'.")


@plugin.include
@group.child
@crescent.command(
    name="entrypoint",
    description="Create an entrypoint message for a ticket configuration.",
)
class CreateEntrypoint:
    name = crescent.option(
        str,
        "The name of the ticket configuration to create an entrypoint for.",
        autocomplete=ticket_config_autocomplete,
    )
    content = crescent.option(str, "The content of the message.")
    button = crescent.option(str, "The button label.")

    async def callback(self, ctx: crescent.Context) -> None:
        await ctx.respond("todo")
