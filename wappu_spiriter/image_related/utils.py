from io import BytesIO
import matplotlib.pyplot as plt
from PIL import Image


def show_pil_image(image: Image.Image) -> None:
    plt.imshow(image)
    plt.show()


def pil_image_to_bytes(image: Image.Image) -> bytes:
    image_bytes = BytesIO()
    image.save(image_bytes, format="WEBP")
    image_bytes.seek(0)
    return image_bytes.getvalue()
