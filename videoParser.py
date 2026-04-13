import cv2
import SolarPanelStatusViT
import os
#from glob import glob

#import IPython.display as ipd
#from tqdm.notebook import tqdm

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

def main(fileName):
    try:
        os.mkdir("videoImages")
        answer=videoParse(fileName)
        os.rmdir("videoImages")
        if(answer[1]==True):
            return "dirty"
        elif(answer[0]):
            return "no_panel"
        else:
            return "clean"
        
            
    except Exception as e:
        print("couldnt parse video",e)

if __name__ =="__main__":
    main()