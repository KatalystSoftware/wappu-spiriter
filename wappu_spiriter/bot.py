import logging
from pathlib import Path
from shutil import rmtree
from typing import Dict, List, Tuple, TypedDict

from PIL import Image
from telegram import Update, constants
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
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


async def save_sticker_to_file(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.message.sticker:
        logger.error("No message in update", update, context)
        return

    sticker = update.message.sticker
    logger.info(sticker)

    sticker_file = await context.bot.get_file(sticker)
    logger.info(sticker_file)
    file_extension = (
        sticker_file.file_path.split(".")[-1] if sticker_file.file_path else "webp"
    )
    file_name = f"{sticker_file.file_id}.{file_extension}"
    logger.info(file_name)

    tmp_dir = Path("tmp") / str(update.message.chat.id)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    sticker_path = tmp_dir / file_name
    await sticker_file.download_to_drive(sticker_path)

    template = templates["blank"]
    template_dir = Path("image_templates")
    blank_template = template_dir / template["file_name"]
    slot = template["slots"][0]

    template_image = Image.open(blank_template)
    img_to_insert = Image.open(sticker_path).resize(slot["size"])
    template_image.paste(img_to_insert, slot["position"])

    combined_file_name = tmp_dir / "combined.webp"
    template_image.save(combined_file_name)

    with open(combined_file_name, "rb") as combined_file_name:
        await update.message.reply_document(document=combined_file_name)

    # clean up tmp files
    rmtree(tmp_dir)


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

    active_game = context.bot_data.get(update.message.chat_id)
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
    active_game = (status_message.id, joined_players, has_started)
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

    active_game = context.bot_data.get(update.message.chat_id)
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
    app.add_handler(MessageHandler(filters.Sticker.STATIC, save_sticker_to_file))

    app.run_polling()
