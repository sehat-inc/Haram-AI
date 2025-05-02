import os
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from ocr.ocr_processor import OCRProcessor
from model.inference import infer

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup code (if any)
    yield
    # Shutdown code - cleanup temporary files
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)

# Create temporary directory for uploads
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Haram-AI API",
    description="API for processing food product images and classifying as halaal or haram",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize OCR processor
ocr_processor = OCRProcessor()

@app.get("/")
async def root():
    return {"message": "Welcome to Haram-AI API"}

@app.post("/analyze-ingredients")
async def analyze_ingredients(file: UploadFile = File(...)) -> JSONResponse:
    """
    Process an image file, extract ingredients, and determine if it's halal or haram.
    
    Args:
        file: Uploaded image file
        
    Returns:
        String containing the classification result
    """
    try:
        # Validate file type
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only JPEG, PNG, GIF, BMP, and WebP images are allowed."
            )

        # Save uploaded file temporarily
        temp_path = UPLOAD_DIR / file.filename
        try:
            with temp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            await file.close()

        # Process the image with OCR
        ingredients_text = await ocr_processor.process_image(str(temp_path))
        

        # Clean up temporary file
        if temp_path.exists():
            os.remove(temp_path)

        if ingredients_text.startswith("Error"):
            raise HTTPException(status_code=500, detail=ingredients_text)

        # Create intermediate JSONResponse for inference
        ingredients_json = JSONResponse(
            content={
                "status": "success",
                "ingredients": ingredients_text
            }
        )
        if ingredients_text == 'no':
            classification = "No ingredient list found"

            return JSONResponse(content=
                            {"classification": classification}
                            )
        else:
            # Get halal/haram classification
           
            classification = infer(ingredients_json)
            
            return JSONResponse(content=
                                {"classification": classification}
                                )

    except HTTPException as he:
        raise he
    except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))
