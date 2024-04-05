import logging
from pathlib import Path
from shutil import rmtree
from typing import Dict, List, Tuple, TypedDict

from PIL import Image
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
