import asyncio
import typing as t

import crescent
import flare
import hikari

from wires import constants
from wires.database.models import Highlight, User
from wires.utils import clip, unwrap

from . import Plugin

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
    if not message:
        assert user_id
        select = SelectHighlight(current)
        create = CreateHighlightButton(user_id)
    else:
        select = t.cast(
            "SelectHighlight",
            await SelectHighlight.from_partial(message.components[1].components[0]),
        )
        select.current = current

        create = t.cast(
            "CreateHighlightButton",
            await CreateHighlightButton.from_partial(
                message.components[0].components[0]
            ),
        )
        user_id = create.user_id

    highlights = await Highlight.fetch_for_user(user_id)
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

    first_row = flare.Row(create)
    if current:
        first_row.append(EditHighlightButton(current))
        first_row.append(DeleteHighlightButton(current))
    rows = await asyncio.gather(first_row, flare.Row(select))

    return {
        "content": "hi",
        "components": rows,
    }


class CreateHighlightButton(flare.Button, label="New"):
    user_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
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


class EditHighlightButton(flare.Button, label="Edit"):
    highlight_id: int

    async def callback(self, ctx: flare.MessageContext) -> None:
        hl = await Highlight.fetch(id=self.highlight_id)
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
        hl = await Highlight.fetch(id=self.highlight_id)
        hl.content = unwrap(self.content.value)
        await hl.save()
        await ctx.edit_response(
            **await highlight_view_msg(None, hl.id, ctx.interaction.message)
        )
