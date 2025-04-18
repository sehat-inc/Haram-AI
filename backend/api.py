from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/ocr")
async def ocr():
    
    # will be imported from ocr module
    return
    