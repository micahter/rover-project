import cv2
import SolarPanelStatusViT
#from glob import glob
import os
import shutil
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi import WebSocket
import asyncio

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
VIDEO_UPLOAD_DIR="videoUploads"
os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)
VIDEO_IMAGES="videoImages"
os.makedirs(VIDEO_IMAGES, exist_ok=True)
@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):

    # Safe filename handling
    filename = os.path.basename(file.filename)
    file_location = os.path.join(UPLOAD_DIR, filename)

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        answer = SolarPanelStatusViT.predict(file_location)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
    confidence=(answer[1]*100.0)
    if(answer[0]==1):
        result=f"dirty with a confidence level of {confidence:.2f}%"
    elif(answer[0]==2):
        result =f"no panel detected with a confidence level of {confidence:.2f}%"
    else:
        result=f"clean with a confidence level of {confidence:.2f}%"
    
    return {
        "filename": filename,
        "path": file_location,
        "result": result
        }

@app.post("/uploadVid")
async def upload_video(file: UploadFile = File(...)):
    filename= os.path.basename(file.filename)
    file_location = os.path.join(VIDEO_UPLOAD_DIR,filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": filename}
    

@app.websocket("/ws/video/{filename}")
async def stream_video(websocket: WebSocket, filename: str):
    await websocket.accept()

    file_location = os.path.join(VIDEO_UPLOAD_DIR,filename)

    cap= cv2.VideoCapture(file_location)
    #frame_count= int (cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_idx = 0
    

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % 20==0:
            #image_path = os.path.join(VIDEO_IMAGES, f"image_{img_idx}.jpg")
            cv2.imwrite("temp.jpg", frame)
            try:
                answer = SolarPanelStatusViT.predict("temp.jpg")
                confidence = float(answer[1]) * 100
                if(answer[0]==1):
                    result="dirty"
                elif(answer[0]==2):
                    result =f"no panel"
                else:
                    result="clean"

                success, buffer = cv2.imencode(".jpg", frame)
                if not success:
                    frame_idx +=1
                    continue
                frame_bytes = buffer.tobytes()

                await websocket.send_json({
                    "frame":frame_idx,
                    "label": result,
                    "confidence": f"{confidence:.2f}",
                    "image": frame_bytes.hex()

                })

                await asyncio.sleep(.2)
            except Exception as e:
                    await websocket.send_json({"error": str(e)})
        frame_idx+=1
    
    cap.release()
    await websocket.close()

    


