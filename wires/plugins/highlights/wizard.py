import asyncio
import typing as t

import crescent
import flare
import hikari

from wires import constants
from wires.database.models import Highlight, User
from wires.utils import clip, unwrap

from .. import Plugin

plugin = Plugin()


@plugin.include
@crescent.command(name="highlights", description="View and manage your highlights.")
async def _(ctx: crescent.Context) -> None:
    await ctx.respond(
        **await highlight_view_msg(ctx.user.id, None, None), ephemeral=True
    )


async def highlight_view_msg(
    user_id: int | None,
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
        assert user_id
        select = SelectHighlight(current)
        create = CreateHighlightButton(user_id)
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

    highlights = await Highlight.fetch_for_user(user_id)
    create = create.set_disabled(len(highlights) >= constants.MAX_HIGHLIGHTS_PER_USER)
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
    rows = await asyncio.gather(flare.Row(select), row)

    if hl:
        embed = hikari.Embed(
            description=f"```{'re' if hl.is_regex else ''}\n{hl.content}\n```",
            color=constants.EMBED_DARK_BG,
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
        "components": rows,
    }


class CreateHighlightButton(flare.Button, label="New"):
    user_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        total = await Highlight.count(user_id=self.user_id)
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
            **await highlight_view_msg(None, None, unwrap(ctx.message))
        )


class ToggleIsRegex(flare.Button):
    highlight_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        hl = await Highlight.exists(id=self.highlight_id)
        if hl:
            hl.is_regex = not hl.is_regex
            await hl.save()
        await ctx.edit_response(
            **await highlight_view_msg(None, hl.id if hl else None, ctx.message)
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
                **await highlight_view_msg(None, None, ctx.interaction.message)
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
            **await highlight_view_msg(None, self.current, unwrap(ctx.message))
        )


class CreateHighlightModal(flare.Modal, title="Create Highlight"):
    user_id: int

    content: flare.TextInput = flare.TextInput(
        "Highlight content", max_length=constants.MAX_HIGHLIGHT_LENGTH
    )

    async def callback(self, ctx: flare.ModalContext) -> None:
        total = await Highlight.count(user_id=self.user_id)
        if total >= constants.MAX_HIGHLIGHTS_PER_USER:
            await ctx.respond(
                "You can only have up to 24 highlights.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return

        await User.get_or_create(self.user_id)
        hl = await Highlight(
            user_id=self.user_id, content=unwrap(self.content.value)
        ).create()
        await ctx.edit_response(
            **await highlight_view_msg(self.user_id, hl.id, ctx.interaction.message)
        )


class EditHighlightModal(flare.Modal, title="Edit Highlight"):
    highlight_id: int

    content: flare.TextInput = flare.TextInput(
        "Highlight content", max_length=constants.MAX_HIGHLIGHT_LENGTH
    )

    async def callback(self, ctx: flare.ModalContext) -> None:
        hl = await Highlight.exists(id=self.highlight_id)
        if hl:
            hl.content = unwrap(self.content.value)
            await hl.save()

        await ctx.edit_response(
            **await highlight_view_msg(
                None, hl.id if hl else None, ctx.interaction.message
            )
        )

        if not hl:
            await ctx.respond(
                "That highlight was deleted.", flags=hikari.MessageFlag.EPHEMERAL
            )
