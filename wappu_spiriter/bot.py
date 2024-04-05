import logging
from pathlib import Path

from telegram import Update
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

    sticker_dir = Path("tmp/stickers")
    sticker_dir.mkdir(parents=True, exist_ok=True)
    await sticker_file.download_to_drive(sticker_dir / file_name)

    await update.message.reply_sticker(sticker=sticker)


async def hello_world(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        logger.error("No message in update", update, context)
        return

    await update.message.reply_text("Hello, world!")


def main() -> None:
    # pydantic dotenv is dumb here
    settings = Settings()  # type: ignore
    persistence = PicklePersistence(filepath="data.pickle")
    app = (
        ApplicationBuilder().token(settings.bot_token).persistence(persistence).build()
    )

    app.add_handler(CommandHandler("start", hello_world))
    app.add_handler(MessageHandler(filters.Sticker.STATIC, save_sticker_to_file))

    app.run_polling()
