import base64
from openai import AsyncOpenAI
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def generate_thumbnail(prompt:str, style_prompt:str, headshot_url: str)->bytes:
    """ Use the response API with gpt-image-2 as a built-in image-generation tool.
        Pass Headshot url directly as an input_image
        Returns raw PNG data as bytes
    """
    full_prompt = (
        f"{style_prompt} \n\n"
        f"User prompt: {prompt} \n\n"
        "Important: The generated thumbnail MUST prominently feature the person"
        "shown in the provided reference headshot photo. Keep their likeness accurate"
    )
    response = await client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role":"user",
                "content":[
                    {"type":"input_image","image_url":headshot_url},
                    {"type":"input_text","text":full_prompt}
                ]
            }
        ],
        tools=[
            {"type":"image_generation",
            "model":"gpt-image-2",
            "size":"1024x1536",
            "quality":"medium",
            "output_format":"png"
            }
        ]
    )
    for item in response.content:
        if item.type =="image_generation_call" and item.result:
            return base64.b64decode(item.result)
    raise RuntimeError("No image generation result found in the response")

    