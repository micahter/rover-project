import cv2
import SolarPanelStatusViT
#from glob import glob
import os
import shutil
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

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

def videoParse(filename):
    cap= cv2.VideoCapture(filename)
    frame_count= int (cap.get(cv2.CAP_PROP_FRAME_COUNT))
    img_idx = 0
    
    
    save_path= "Users/Micah/OneDrive/Desktop/code/rover-project/videoImages"
    for frame in range(frame_count):
        img = cap.read()
        if frame % 20:
            cv2.imwrite(os.path.join(save_path,"videoImages/image_{img_idx}".format(img_idx)),img)
            img_idx+=1
    no_panel=True
    dirty=False
    for frame in os.listdir(save_path):
        isDirtyStatus = SolarPanelStatusViT(frame)
        if isDirtyStatus=='1':
            no_panel=False
            dirty= True
        if isDirtyStatus =='0':
            no_panel= False
    os.rmdir("videoImages")
    return [no_panel, dirty]


