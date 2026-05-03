import os
import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file.")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

async def test_gemini_image_generation():
    headshot_url = "https://ik.imagekit.io/hy9i34jbr/headshots/GOBI_1__KrrvOhsj.png"
    prompt = "Create a bold, dramatic Youtube thumbnail with high contrast, cinematic lighting, dark moody background, and powerful composition. The person's face should be prominent with a dramatic expression."
    
    print(f"Downloading headshot from: {headshot_url}")
    async with httpx.AsyncClient() as httpx_client:
        image_response = await httpx_client.get(headshot_url)
        if image_response.status_code != 200:
            print(f"Failed to download image: {image_response.status_code}")
            return
        image_bytes = image_response.content

    print("Generating image with Gemini...")
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Using Gemini 2.5 Flash with image output modality
            response = client.models.generate_content(
                model='gemini-2.5-flash-image',
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    f"User prompt: {prompt}\n\nImportant: The generated thumbnail MUST prominently feature the person shown in the provided reference headshot photo. Keep their likeness accurate."
                ],
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE']
                )
            )

            # Process the response
            image_part = None
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image_part = part.inline_data
                        break
            
            if image_part:
                output_path = "test_thumbnail.png"
                with open(output_path, "wb") as f:
                    f.write(image_part.data)
                print(f"Success! Image saved to {output_path}")
                return
            else:
                print("No image data found in the response.")
                print("Response:", response)
                return

        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < max_retries - 1:
                    print(f"Quota exceeded (429). Retrying in {retry_delay}s...")
                    import asyncio as a
                    await a.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    print(f"Failed after {max_retries} attempts: API Quota exhausted. Please check your plan at https://aistudio.google.com/app/plan_and_billing")
                    return
            print(f"An error occurred: {e}")
            return

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gemini_image_generation())
