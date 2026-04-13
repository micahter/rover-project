#This file should basically never be touched going forward, this is the state of the pretrained ViT model
import torch
import torchmetrics
import torch.nn as nn
import lightning as L
from pytorch_pretrained_vit import ViT
import torch.nn.functional as F


class ViTModel_pretrained(L.LightningModule):
    def __init__(self, lr=1e-4, class_weights=None):
        super().__init__()
        # Change task to 'multiclass' and specify num_classes
        self.accuracy = torchmetrics.Accuracy(task='multiclass', num_classes=3)
        self.val_accuracy = torchmetrics.Accuracy(task='multiclass', num_classes=3)
        self.vit = ViT('B_16_imagenet1k', pretrained=True)
        
        for param in self.vit.parameters():
          param.requires_grad = False

        self.vit.fc = nn.Linear(self.vit.fc.in_features, 3)
        self.class_weights = class_weights # Store class weights


    def forward(self, x):
        return self.vit(x)
    def configure_optimizers(self):
        return torch.optim.Adam(self.vit.fc.parameters(), lr=1e-4)
    def training_step(self, batch, batch_idx):

        input, target = batch
        out = self.forward(input)
        # Use weighted CrossEntropyLoss if weights are provided
        if self.class_weights is not None:
            loss = F.cross_entropy(out, target, weight=self.class_weights.to(self.device))
        else:
            loss = F.cross_entropy(out, target)
        acc = self.val_accuracy(out, target)
        self.log("train_loss", loss, prog_bar=True, on_step=True, on_epoch=True)
        self.log("train_acc", acc, prog_bar=True, on_step=True, on_epoch=True)
        return loss