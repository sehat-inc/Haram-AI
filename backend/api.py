import os
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from ocr.ocr_processor import OCRProcessor


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
   description="API for processing food product images and extracting ingredients",
   version="1.0.0",
   lifespan=lifespan
)

# Initialize OCR processor
ocr_processor = OCRProcessor()

@app.get("/")
async def root():
   return {"message": "Welcome to Haram-AI API"}

@app.post("/ocr")
async def ocr(file: UploadFile = File(...)) -> JSONResponse:
   """
   Process an image file and extract ingredients information.
   
   Args:
       file: Uploaded image file
       
   Returns:
       JSONResponse containing the extracted ingredients or error message
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

       # Process the image
       result = await ocr_processor.process_image(str(temp_path))

       # Clean up
       if temp_path.exists():
           os.remove(temp_path)

       if result.startswith("Error"):
           raise HTTPException(status_code=500, detail=result)

       return JSONResponse(
           content={
               "status": "success",
               "ingredients": result
           }
       )

   except HTTPException as he:
       raise he
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))