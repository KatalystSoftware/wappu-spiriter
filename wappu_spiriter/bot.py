import io
import logging
from typing import Dict, List, Tuple, TypedDict

import matplotlib.pyplot as plt
from PIL import Image
from telegram import Update, constants
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
)

from wappu_spiriter.settings import Settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class Slot(TypedDict):
    position: Tuple[int, int]
    size: Tuple[int, int]
    prompts: List[str]


class ImageTemplate(TypedDict):
    file_name: str
    size: Tuple[int, int]
    slots: List[Slot]


templates: Dict[str, ImageTemplate] = {
    "blank": {
        "file_name": "blank.webp",
        "size": (1024, 512),
        "slots": [
            {
                "position": (256, 128),
                "size": (256, 256),
                "prompts": ["sticker"],
            }
        ],
    }
}


def show_pil_image(image: Image.Image) -> None:
    plt.imshow(image)
    plt.show()


ActiveGame = Tuple[int, set[int], bool]


async def get_picture_pil_image_from_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_type: str = "photo",
) -> Image.Image:
    assert update.message and getattr(update.message, file_type)

    picture = getattr(update.message, file_type)
    picture_file = await context.bot.get_file(picture[-1])
    picture_byte_array = await picture_file.download_as_bytearray()
    pil_image = Image.open(io.BytesIO(picture_byte_array))

    return pil_image


async def get_sticker_pil_image_from_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Image.Image:
    assert update.message and update.message.sticker

    sticker = update.message.sticker
    sticker_file = await context.bot.get_file(sticker)
    sticker_byte_array = await sticker_file.download_as_bytearray()
    pil_image = Image.open(io.BytesIO(sticker_byte_array))

    return pil_image


async def overlay_pil_image_on_base_image(
    base_image: Image.Image,
    overlay_image: Image.Image,
    target_coordinates: Tuple[Tuple[int, int], Tuple[int, int]],
) -> Image.Image:
    scaled_overlay = overlay_image.resize(
        (
            target_coordinates[1][0] - target_coordinates[0][0],
            target_coordinates[1][1] - target_coordinates[0][1],
        )
    )
    copied_base_image = base_image.copy()
    copied_base_image.paste(scaled_overlay, target_coordinates[0])
    return copied_base_image


async def tick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.sticker:
        pil_image = await get_sticker_pil_image_from_message(update, context)
        # print("Got sticker", show_pil_image(pil_image))

    if update.message and update.message.photo:
        pil_image = await get_picture_pil_image_from_message(update, context)
        # print("Got photo", show_pil_image(pil_image))


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        logger.error("No message in update", update, context)
        return

    if (
        update.message.chat.type != constants.ChatType.GROUP
        and update.message.chat.type != constants.ChatType.SUPERGROUP
    ):
        await update.message.reply_text("Games can only be started in group chats!")
        return

    active_game: ActiveGame | None = context.bot_data.get(update.message.chat_id)
    if active_game is None:
        await update.message.reply_text("First create a game with /new!")
        return
    status_message_id, previously_joined_players, has_started = active_game
    has_started = True

    context.bot_data[update.message.chat_id] = (
        status_message_id,
        previously_joined_players,
        has_started,
    )

    await context.bot.edit_message_text(
        f"""New game created\\!
        
🖼️ Game started\\!

👤 {len(previously_joined_players)} players joined\\!

[Play game](https://t.me/{context.bot.username})""",
        update.message.chat_id,
        status_message_id,
        parse_mode=constants.ParseMode.MARKDOWN_V2,
    )


async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.from_user:
        logger.error("No message or user in update", update, context)
        return

    if (
        update.message.chat.type != constants.ChatType.GROUP
        and update.message.chat.type != constants.ChatType.SUPERGROUP
    ):
        await update.message.reply_text("This command is only usable in group chats!")
        return

    joined_players = set([update.message.from_user.id])

    status_message = await update.message.reply_text(
        f"""New game created!
        
⌛ Waiting for players to /join...

👤 {len(joined_players)} players joined!

Commands:
/join - join game
/start - start game"""
    )

    has_started = False
    active_game: ActiveGame = (status_message.id, joined_players, has_started)
    context.bot_data[update.message.chat_id] = active_game
    context.bot_data[update.message.from_user.id] = update.message.chat_id

    logger.info(active_game)
    logger.info(update.message.chat_id)


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.from_user:
        logger.error("No message or user in update", update, context)
        return

    if (
        update.message.chat.type != constants.ChatType.GROUP
        and update.message.chat.type != constants.ChatType.SUPERGROUP
    ):
        await update.message.reply_text("This command is only usable in group chats!")
        return

    active_game: ActiveGame | None = context.bot_data.get(update.message.chat_id)
    if active_game is None:
        await update.message.reply_text("First create a game with /new!")
        return
    status_message_id, previously_joined_players, has_started = active_game

    if has_started:
        await update.message.reply_text(
            "Game has already started, wait for the next one!"
        )

    chat_admin_ids = [
        admin.user.id for admin in await update.message.chat.get_administrators()
    ]
    bot_is_admin = context.bot.id in chat_admin_ids
    if bot_is_admin:
        await update.message.delete()

    user_already_joined = update.message.from_user.id in previously_joined_players
    if user_already_joined:
        return

    joined_players = set(
        list(previously_joined_players) + [update.message.from_user.id]
    )
    context.bot_data[update.message.chat_id] = (status_message_id, joined_players)
    context.bot_data[update.message.from_user.id] = update.message.chat_id

    await context.bot.edit_message_text(
        f"""New game created!
        
⌛ Waiting for players to /join...

👤 {len(joined_players)} players joined!

Commands:
/join - join game
/start - start game""",
        update.message.chat_id,
        status_message_id,
    )


def main() -> None:
    # pydantic dotenv is dumb here
    settings = Settings()  # type: ignore
    persistence = PicklePersistence(filepath="data.pickle")
    app = (
        ApplicationBuilder().token(settings.bot_token).persistence(persistence).build()
    )

    app.add_handler(CommandHandler("start", start_game))
    app.add_handler(CommandHandler("new", new_game))
    app.add_handler(CommandHandler("join", join_game))
    app.add_handler(MessageHandler(None, tick))

    app.run_polling()  # todo: shorten polling time
