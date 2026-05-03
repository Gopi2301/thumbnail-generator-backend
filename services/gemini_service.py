import httpx
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

async def generate_thumbnail(prompt: str, style_prompt: str, headshot_url: str) -> bytes:
    """ Use Gemini 2.0 Flash to generate a thumbnail based on a headshot and prompt.
        Returns raw PNG/JPEG data as bytes.
    """
    full_prompt = (
        f"{style_prompt} \n\n"
        f"User prompt: {prompt} \n\n"
        "Important: The generated thumbnail MUST prominently feature the person "
        "shown in the provided reference headshot photo. Keep their likeness accurate."
    )

    # Download the headshot image
    async with httpx.AsyncClient() as httpx_client:
        image_response = await httpx_client.get(headshot_url)
        if image_response.status_code != 200:
            raise RuntimeError(f"Failed to download headshot: {image_response.status_code}")
        image_bytes = image_response.content

    max_retries = 3
    retry_delay = 5 # seconds
    
    for attempt in range(max_retries):
        try:
            # Using Gemini 2.5 Flash with image output modality
            response = client.models.generate_content(
                model='gemini-2.5-flash-image',
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    full_prompt
                ],
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE']
                )
            )

            # Extract the image bytes from the response
            image_part = None
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image_part = part.inline_data
                        break
            
            if not image_part:
                # Log response for debugging if no image is found
                logger.error(f"No image data found. Response: {response}")
                raise RuntimeError("No image data found in the Gemini response. The model might have refused to generate the image or the modality is unavailable.")

            return image_part.data

        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_retries - 1:
                    print(f"Quota exceeded (429). Retrying in {retry_delay}s (Attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                    continue
                else:
                    raise RuntimeError(
                        "Gemini API quota exhausted (429). If you are on the Free Tier, "
                        "image generation might be restricted or you may have hit your daily limit. "
                        "Please check your quota at https://aistudio.google.com/app/plan_and_billing"
                    )
            raise RuntimeError(f"Gemini image generation failed: {str(e)}")
