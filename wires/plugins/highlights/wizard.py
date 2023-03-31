import asyncio
import typing as t

import crescent
import flare
import hikari
from regex_rs import Regex

from wires import constants
from wires.database.models import Guild, Highlight, User
from wires.utils import clip, unwrap

from .. import Plugin

plugin = Plugin()


@plugin.include
@crescent.command(
    name="highlights",
    description="View and manage your highlights.",
    dm_enabled=False,
)
async def _(ctx: crescent.Context) -> None:
    assert ctx.guild_id
    await ctx.respond(
        **await highlight_view_msg(ctx.user.id, ctx.guild_id, None, None),
        ephemeral=True,
    )


async def highlight_view_msg(
    user_id: int | None,
    guild_id: int | None,
    current: int | None,
    message: hikari.Message | None,
) -> dict[str, t.Any]:
    if current:
        hl = await Highlight.exists(id=current)
        if not hl:
            current = None
    else:
        hl = None

    if not message:
        assert user_id and guild_id
        select = SelectHighlight(current)
        create = CreateHighlightButton(user_id, guild_id)
    else:
        select = t.cast(
            "SelectHighlight",
            await SelectHighlight.from_partial(message.components[0].components[0]),
        )
        select.current = current

        create = t.cast(
            "CreateHighlightButton",
            await CreateHighlightButton.from_partial(
                message.components[1].components[0]
            ),
        )
        user_id = create.user_id
        guild_id = create.guild_id

    highlights = await Highlight.fetchmany(user_id=user_id, guild_id=guild_id)
    create.set_disabled(len(highlights) >= constants.MAX_HIGHLIGHTS_PER_USER)
    select.set_options(
        *(
            hikari.SelectMenuOption(
                label="Overview",
                value="_",
                description=None,
                emoji=None,
                is_default=select.current is None,
            ),
            *(
                hikari.SelectMenuOption(
                    label=f"Highlight '{clip(hl.content, 12)}'",
                    value=str(hl.id),
                    description=None,
                    emoji=None,
                    is_default=hl.id == select.current,
                )
                for hl in highlights
            ),
        )
    )

    rows = [flare.Row(select)]

    row = flare.Row(create)
    if current:
        assert hl
        row.append(EditHighlightButton(current))
        toggle_regex = ToggleIsRegex(current)
        if hl.is_regex:
            toggle_regex.set_label("Regex: Yes")
        else:
            toggle_regex.set_label("Regex: No")
        row.append(toggle_regex)
        row.append(DeleteHighlightButton(current))
        rows.append(row)
        rows.append(flare.Row(SelectIgnoredChannels(current)))
        rows.append(flare.Row(SelectIgnoredUsers(current)))

        c_label = "Blacklist" if hl.channel_list_is_blacklist else "Whitelist"
        u_label = "Blacklist" if hl.user_list_is_blacklist else "Whitelist"
        rows.append(
            flare.Row(
                ToggleChannelListMode(current).set_label(f"Channel List: {c_label}"),
                ToggleUserListMode(current).set_label(f"User List: {u_label}"),
            )
        )
    else:
        rows.append(row)
    rows_final = await asyncio.gather(*rows)

    if hl:
        embed = hikari.Embed(
            description=f"```{'re' if hl.is_regex else ''}\n{hl.content}\n```",
            color=constants.EMBED_DARK_BG,
        )
        if hl.is_regex:
            try:
                Regex(hl.content)
            except BaseException as e:
                embed.add_field("Error", f"```re\n{e.args[0]}\n```")
        if hl.channel_list:
            mode = "Ignored" if hl.channel_list_is_blacklist else "Allowed"
            embed.add_field(
                f"{mode} Channels", ", ".join(f"<#{id}>" for id in hl.channel_list)
            )
        if hl.user_list:
            mode = "Ignored" if hl.user_list_is_blacklist else "Allowed"
            embed.add_field(
                f"{mode} Users", ", ".join(f"<@{id}>" for id in hl.user_list)
            )

    elif highlights:
        embed = hikari.Embed(
            description="- " + "\n- ".join(clip(hl.content, 12) for hl in highlights),
            color=constants.EMBED_DARK_BG,
        )
    else:
        embed = hikari.Embed(
            description="You don't have any highlights.",
            color=constants.EMBED_DARK_BG,
        )

    return {
        "embed": embed,
        "components": rows_final,
    }


class CreateHighlightButton(flare.Button, label="New"):
    user_id: int
    guild_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        total = await Highlight.count(user_id=self.user_id, guild_id=self.guild_id)
        if total >= constants.MAX_HIGHLIGHTS_PER_USER:
            await ctx.respond(
                "You can only have up to 24 highlights.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
        else:
            await CreateHighlightModal(self.user_id).send(ctx.interaction)


class DeleteHighlightButton(
    flare.Button, label="Delete", style=hikari.ButtonStyle.DANGER
):
    highlight_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        await Highlight.delete_query().where(id=self.highlight_id).execute()
        await ctx.edit_response(
            **await highlight_view_msg(None, None, None, unwrap(ctx.message))
        )


class ToggleIsRegex(flare.Button):
    highlight_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        hl = await Highlight.exists(id=self.highlight_id)
        if hl:
            hl.is_regex = not hl.is_regex
            await hl.save()
        await ctx.edit_response(
            **await highlight_view_msg(None, None, hl.id if hl else None, ctx.message)
        )
        if not hl:
            await ctx.respond(
                "That highlight was deleted.", flags=hikari.MessageFlag.EPHEMERAL
            )


class ToggleChannelListMode(flare.Button):
    highlight_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        hl = await Highlight.exists(id=self.highlight_id)
        if hl:
            hl.channel_list_is_blacklist = not hl.channel_list_is_blacklist
            await hl.save()

        await ctx.edit_response(
            **await highlight_view_msg(None, None, hl.id if hl else None, ctx.message)
        )
        if not hl:
            await ctx.respond(
                "That highlight was deleted.", flags=hikari.MessageFlag.EPHEMERAL
            )


class ToggleUserListMode(flare.Button):
    highlight_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        hl = await Highlight.exists(id=self.highlight_id)
        if hl:
            hl.user_list_is_blacklist = not hl.user_list_is_blacklist
            await hl.save()

        await ctx.edit_response(
            **await highlight_view_msg(None, None, hl.id if hl else None, ctx.message)
        )
        if not hl:
            await ctx.respond(
                "That highlight was deleted.", flags=hikari.MessageFlag.EPHEMERAL
            )


class EditHighlightButton(flare.Button, label="Edit"):
    highlight_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        hl = await Highlight.exists(id=self.highlight_id)
        if not hl:
            await ctx.edit_response(
                **await highlight_view_msg(None, None, None, ctx.interaction.message)
            )
            await ctx.respond(
                "That highlight was deleted.", flags=hikari.MessageFlag.EPHEMERAL
            )
            return
        modal = EditHighlightModal(self.highlight_id)
        modal.content.set_value(hl.content)
        await modal.send(ctx.interaction)


class SelectHighlight(flare.TextSelect):
    current: int | None

    async def callback(self, ctx: flare.MessageContext) -> None:
        self.current = (
            int(ctx.values[0]) if ctx.values and ctx.values[0] != "_" else None
        )
        await ctx.edit_response(
            **await highlight_view_msg(None, None, self.current, unwrap(ctx.message))
        )


class SelectIgnoredChannels(
    flare.ChannelSelect, min_values=0, max_values=25, placeholder="Channels"
):
    highlight_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        hl = await Highlight.exists(id=self.highlight_id)
        if hl:
            hl.channel_list = [c.id for c in ctx.channels]
            await hl.save()

        await ctx.edit_response(
            **await highlight_view_msg(None, None, hl.id if hl else None, ctx.message)
        )
        if not hl:
            await ctx.respond(
                "That highlight was deleted.", flags=hikari.MessageFlag.EPHEMERAL
            )


class SelectIgnoredUsers(
    flare.UserSelect, min_values=0, max_values=25, placeholder="Users"
):
    highlight_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        hl = await Highlight.exists(id=self.highlight_id)
        if hl:
            hl.user_list = [u.id for u in ctx.users]
            await hl.save()

        await ctx.edit_response(
            **await highlight_view_msg(None, None, hl.id if hl else None, ctx.message)
        )
        if not hl:
            await ctx.respond(
                "That highlight was deleted.", flags=hikari.MessageFlag.EPHEMERAL
            )


class CreateHighlightModal(flare.Modal, title="Create Highlight"):
    user_id: int

    content: flare.TextInput = flare.TextInput(
        "Highlight content",
        max_length=constants.MAX_HIGHLIGHT_LENGTH,
        style=hikari.TextInputStyle.PARAGRAPH,
    )

    async def callback(self, ctx: flare.ModalContext) -> None:
        guild_id = unwrap(ctx.guild_id)
        total = await Highlight.count(user_id=self.user_id, guild_id=guild_id)
        if total >= constants.MAX_HIGHLIGHTS_PER_USER:
            await ctx.respond(
                "You can only have up to 24 highlights.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return

        await User.get_or_create(self.user_id)
        await Guild.get_or_create(guild_id)
        hl = await Highlight(
            user_id=self.user_id,
            guild_id=guild_id,
            content=unwrap(self.content.value),
        ).create()
        await ctx.edit_response(
            **await highlight_view_msg(None, None, hl.id, ctx.interaction.message)
        )


class EditHighlightModal(flare.Modal, title="Edit Highlight"):
    highlight_id: int

    content: flare.TextInput = flare.TextInput(
        "Highlight content",
        max_length=constants.MAX_HIGHLIGHT_LENGTH,
        style=hikari.TextInputStyle.PARAGRAPH,
    )

    async def callback(self, ctx: flare.ModalContext) -> None:
        hl = await Highlight.exists(id=self.highlight_id)
        if hl:
            hl.content = unwrap(self.content.value)
            await hl.save()

        await ctx.edit_response(
            **await highlight_view_msg(
                None,
                None,
                hl.id if hl else None,
                ctx.interaction.message,
            )
        )

        if not hl:
            await ctx.respond(
                "That highlight was deleted.", flags=hikari.MessageFlag.EPHEMERAL
            )
