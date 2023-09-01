import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

from wappu_spiriter.settings import Settings

logger = logging.getLogger(__name__)


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

    app.run_polling()
