#import necessary library
#import numpy as np
#import pandas as pd
import os
#import PIL
from PIL import Image

#import matplotlib.pyplot as plt
#import albumentations
import torch
#import torch.nn as nn
#import torchvision
#import pytorch_lightning as pl
#import torchvision.models as models
import torch.nn.functional as F
#import cv2
#from pytorch_pretrained_vit import ViT
#import torchmetrics
#from torchvision.datasets import DatasetFolder
#import lightning as L
import torchvision.transforms as transforms
import ViTModel_pretrained

class_weights = torch.tensor([1.0, 1.35, 1.0], dtype=torch.float)
ViTmodel = ViTModel_pretrained.ViTModel_pretrained(class_weights=class_weights)
checkpoint = torch.load("C:/Users/Micah/OneDrive/Desktop/code/rover-project/epoch=45-val_loss=0.20.ckpt",map_location='cpu')
ViTmodel.load_state_dict(checkpoint["state_dict"])
device = torch.device("cpu")

ViTmodel.to(device)
ViTmodel.eval()

def predict(img_path: str):
    #save_path= "Users/Micah/OneDrive/Desktop/code/rover-project/uploads"
    
    # Pass the class weights to the model
    # clean_count = 2004
    # dirty_count = 1409
    # total_count = clean_count + dirty_count

    # Inverse of class frequencies, scaled. This gives higher weight to the minority class.


    #Calculate class weights

    #add class weights to model

    #add learned params onto pretrained model
    
    image = Image.open(img_path)

    transform = transforms.Compose([
        transforms.Resize((384, 384)), # Example size
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
    ])
    input_tensor=transform(image)

    input_batch = input_tensor.unsqueeze(0).to(device)

    with torch.no_grad():
        output= ViTmodel(input_batch)
    probabilities = F.softmax(output, dim=1)
    predicted_idx = torch.argmax(output, dim=1).item()
    #class_names = ['clean', 'dusty', 'no_panel']
    #predicted_class= class_names[predicted_idx]

    confidence = probabilities[0, predicted_idx].item()
    ans=(predicted_idx,confidence)
    return ans

