from typing import Tuple

from PIL import Image


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
