import matplotlib.pyplot as plt
from PIL import Image


def show_pil_image(image: Image.Image) -> None:
    plt.imshow(image)
    plt.show()
