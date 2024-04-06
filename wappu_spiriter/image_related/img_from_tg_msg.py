import io

from PIL import Image
from telegram import Update

from wappu_spiriter.game_context import GameStateContext


async def get_picture_pil_image_from_message(
    update: Update,
    context: GameStateContext,
    file_type: str = "photo",
) -> Image.Image:
    assert update.message and getattr(update.message, file_type)

    picture = getattr(update.message, file_type)
    picture_file = await context.bot.get_file(picture[-1])
    picture_byte_array = await picture_file.download_as_bytearray()
    pil_image = Image.open(io.BytesIO(picture_byte_array))

    return pil_image


async def get_sticker_pil_image_from_message(
    update: Update, context: GameStateContext
) -> Image.Image:
    assert update.message and update.message.sticker

    sticker = update.message.sticker
    sticker_file = await context.bot.get_file(sticker)
    sticker_byte_array = await sticker_file.download_as_bytearray()
    pil_image = Image.open(io.BytesIO(sticker_byte_array))

    return pil_image
