import os
from io import BytesIO
from typing import Annotated

import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from torchvision import transforms

import mlflow

app = FastAPI()

MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "http://127.0.0.1:5000",
)

model = None

CLASS_NAMES = [
    "Bread",
    "Dairy product",
    "Dessert",
    "Egg",
    "Fried food",
    "Meat",
    "Noodles-Pasta",
    "Rice",
    "Seafood",
    "Soup",
    "Vegetable-Fruit",
]

transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
])


@app.on_event("startup")
def load_model():
    global model

    if os.environ.get("SKIP_MODEL"):
        return

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    model = mlflow.pytorch.load_model(
        "models:/food11@champion",
        map_location="cpu",
    )

    model.eval()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
async def predict(file: Annotated[UploadFile, File()]):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model is not loaded",
        )

    contents = await file.read()

    image = Image.open(
        BytesIO(contents)
    ).convert("RGB")

    tensor = transform(
        image
    ).unsqueeze(0)

    with torch.no_grad():
        output = model(tensor)

    probabilities = torch.softmax(
        output,
        dim=1,
    )

    confidence, predicted_class = torch.max(
        probabilities,
        dim=1,
    )

    return {
        "category": CLASS_NAMES[predicted_class.item()],
        "confidence": float(confidence.item()),
    }