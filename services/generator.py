import asyncio
import logging

from sqlmodel import Session, select
from database import engine
from model import Job, Thumbnail
from services.gemini_service import generate_thumbnail
from services.imagekit_service import upload_file

logger = logging.getLogger(__name__)
  
STYLES={
    "bold_dramatic":(
        "Create a bold, dramatic Youtube thumbnail with high contrast, "
        "cinematic lighting, dark moody background, and powerful composition,"
        "The person's face should be prominent with a dramatic expression."
    ),
    "clean_minimal":(
        "Create a clean, minimal Youtube thumbnail with bright lighting, "
        "white/light background, modern professional asethetic, plenty of "
        "The person's face should be prominent with a neutral/pleasant expression."
    ),
    "vibrant_energetic":(
        "Create a vibrant, energetic Youtube thumbnail with colorful gradients, "
        "dynamic angles, eye-catching popo-art style colors, and energetic composition. "
        "The person's face should be prominent with a happy/excited expression."
    )
}
STYLE_ORDER = ["bold_dramatic", "clean_minimal", "vibrant_energetic"]  

async def generate_single_thumbnail(thumbnail_id: int, prompt: str, headshot_url: str):
    # DB mark -> generating
    with Session(engine) as session:
        thumb = session.get(Thumbnail, thumbnail_id)
        if not thumb:
            return
        thumb.status = "generating"
        style_name = thumb.style
        session.add(thumb)
        session.commit()

    style_prompt = STYLES[style_name]

    # AI call
    try:
        image_byte = await generate_thumbnail(prompt, style_prompt, headshot_url)
        
        # Get job_id for folder structure
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            job_id = thumb.job_id

        # Upload this image
        url = upload_file(
            file_bytes=image_byte, 
            file_name=f"{thumbnail_id}.png",
            folder=f"thumbnails/{job_id}/",
        )

        # DB call save the url +mark uploaded
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            if url:
                thumb.imagekit_url = url
                thumb.status = "uploaded"
                logger.info(f"Thumbnail {thumbnail_id} generated and uploaded successfully")
            else:
                thumb.status = "failed"
                thumb.error_message = "ImageKit upload returned None"
                logger.error(f"Thumbnail {thumbnail_id} upload failed: upload_file returned None")
            session.add(thumb)
            session.commit()
    
    except Exception as e:
        logger.error(f"Failed to generate thumbnail {thumbnail_id}: {str(e)}")
        with Session(engine) as session:
            thumb = session.get(Thumbnail, thumbnail_id)
            if thumb:
                thumb.status = "failed"
                thumb.error_message = str(e)[:500]
                session.add(thumb)
                session.commit()

async def process_job(job_id: int):
    # make job as processing
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return
        job.status = 'processing'
        prompt = job.prompt
        headshot_url = job.headshot_url
        session.add(job)
        session.commit()
        
        # find all thumbnails for this job
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()
        thumbnails_ids = [t.id for t in thumbnails]

    # start one worker for each thumbnail
    tasks = [
        generate_single_thumbnail(tid, prompt, headshot_url)
        for tid in thumbnails_ids
    ]
    # wait for all workers to finish
    await asyncio.gather(*tasks, return_exceptions=True) 

    # mark job as completed / failed
    with Session(engine) as session:
        thumbnails = session.exec(
            select(Thumbnail).where(Thumbnail.job_id == job_id)
        ).all()
        all_failed = all(t.status == "failed" for t in thumbnails)
        
        job = session.get(Job, job_id)
        job.status = "failed" if all_failed else "completed"
        session.add(job)
        session.commit()