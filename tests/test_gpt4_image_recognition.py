import unittest
from PIL import Image

from wappu_spiriter.fetch_score_for_image import fetch_score_for_image, pil_image_to_base64_string

class TestImageRecognition(unittest.TestCase):
    def test_fetch_score_for_image(self):
        pil_image = Image.open("./tests/celebration-image.jpg")
        base64_string = pil_image_to_base64_string(pil_image)
        score = fetch_score_for_image(base64_string)
        
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 10)

if __name__ == '__main__':
    unittest.main()