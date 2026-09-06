import io
import os
import base64
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image, ImageChops, ImageEnhance
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from mrz_math import verify_passport_mrz
from verhoeff_math import validate_aadhaar_verhoeff
from biometrics_aifr import match_faces_aifr
from ocr_engine import process_document_ocr

app = FastAPI(title="Jan Rakshak AI - National Screening Backend", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = "best_forgery_ela_model.pth"

def load_model():
    model = models.resnet18()
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(128, 2)
    )
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
        print(f"[MODEL] Loaded Trained Neural Weights from: {MODEL_PATH}")
    model.to(DEVICE)
    model.eval()
    return model

ai_model = load_model()

def compute_ela_image(image: Image.Image, quality=90):
    buffer = io.BytesIO()
    image.save(buffer, 'JPEG', quality=quality)
    buffer.seek(0)
    compressed = Image.open(buffer)
    ela_im = ImageChops.difference(image, compressed)
    extrema = ela_im.getextrema()
    max_diff = max([ex[1] for ex in extrema]) or 1
    scale_factor = 255.0 / max_diff
    return ImageEnhance.Brightness(ela_im).enhance(scale_factor)

@app.post("/api/ocr-extract")
async def extract_ocr(file: UploadFile = File(...)):
    """
    Dedicated OCR Endpoint: Automatically extracts fields, MRZ, UID, PAN & runs mathematical parity.
    """
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    ocr_results = process_document_ocr(image)
    return ocr_results

@app.post("/api/verify-document")
async def verify_document(
    file: UploadFile = File(...),
    doc_type: str = Form("auto"),
    doc_number: str = Form("")
):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")

    # 1. Compute REAL ELA Heatmap
    ela_img = compute_ela_image(image)
    
    # Convert ELA image to Base64 to send to Frontend
    buffered = io.BytesIO()
    ela_img.save(buffered, format="JPEG")
    ela_base64 = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode()

    # 2. Run PyTorch AI Model
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    tensor = transform(ela_img).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = ai_model(tensor)
        probs = torch.softmax(outputs, dim=1)[0]
        confidence, pred_class = torch.max(probs, 0)

    is_ai_authentic = (pred_class.item() == 0)
    ai_confidence = round(confidence.item() * 100, 1)

    # 3. Intelligent OCR Field Extraction & Math Parity
    ocr_results = process_document_ocr(image)
    doc_classification = ocr_results.get("classification", {})
    
    extracted_num = doc_classification.get("doc_number")
    is_checksum_valid = doc_classification.get("is_checksum_valid", True)
    checksum_type = doc_classification.get("checksum_type", "Algorithmic Checksum")
    
    # Override with manual input if user provided one
    target_num = doc_number.strip() if doc_number.strip() else extracted_num
    
    math_status = "PASSED"
    if target_num:
        if "Aadhaar" in doc_classification.get("doc_type", "") or doc_type.lower() == "aadhaar":
            is_valid = validate_aadhaar_verhoeff(target_num)
            math_status = "PASSED (UIDAI Verhoeff D5 Parity)" if is_valid else "FAILED (Invalid Checksum)"
            is_checksum_valid = is_valid

    overall_verdict = "AUTHENTIC" if (is_ai_authentic and is_checksum_valid) else "FORGERY DETECTED"
    trust_score = ai_confidence if is_ai_authentic else (100 - ai_confidence)
    if not is_checksum_valid:
        trust_score = min(trust_score, 20.0)

    return {
        "filename": file.filename,
        "overall_verdict": overall_verdict,
        "is_authentic": (overall_verdict == "AUTHENTIC"),
        "trust_score": f"{trust_score:.1f}%",
        "ela_confidence": f"{ai_confidence:.1f}%",
        "ela_base64": ela_base64,
        "mathematical_checksum": math_status,
        "ocr_data": doc_classification,
        "raw_text_extracted": ocr_results.get("raw_text_extracted", [])
    }
@app.post("/api/verify-biometrics")
async def verify_biometrics(
    doc_photo: UploadFile = File(...),
    live_photo: UploadFile = File(...)
):
    """
    Biometrics Endpoint: Compares Document Reference Face with Live Webcam Selfie.
    Evaluates Age-Invariant Cosine Metric and 3D Anti-Spoof Liveness.
    """
    doc_bytes = await doc_photo.read()
    live_bytes = await live_photo.read()

    doc_img = Image.open(io.BytesIO(doc_bytes)).convert("RGB")
    live_img = Image.open(io.BytesIO(live_bytes)).convert("RGB")

    match_result = match_faces_aifr(doc_img, live_img)
    return match_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)