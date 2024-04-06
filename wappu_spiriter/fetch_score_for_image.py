import base64
from io import BytesIO
from openai import OpenAI
from PIL import Image

client = OpenAI()

prompt = """
How many points does this image get? End your answer with the "Total points: X" where X is the total number of points you have given.
0, 1 or 2 points from smiling people
0, 1 or 2 points from sodas or other beverages
0, 1 or 2 points from celebration
0, 1 or 2 points from fun time
0, 1 or 2 points from vappu-related stuff
"""


def pil_image_to_base64_string(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def fetch_score_for_image(base64_string: str) -> int:
    print("Calling OPENAI API")

    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_string}"},
                    },
                ],
            }
        ],
        max_tokens=500,
    )

    response_text = response.choices[0].message.content

    assert response_text is not None

    # strip the "Total points: " part
    score = int(response_text.split("Total points: ")[1])

    print("GPT response: ", response_text)
    print("Extracted score: ", score)
    return score
