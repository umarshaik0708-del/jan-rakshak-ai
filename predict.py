import sys
import io
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image, ImageChops, ImageEnhance

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = "best_forgery_ela_model.pth"

# 1. Compute ELA
def compute_ela(image_path, quality=90):
    original = Image.open(image_path).convert('RGB')
    buffer = io.BytesIO()
    original.save(buffer, 'JPEG', quality=quality)
    buffer.seek(0)
    compressed = Image.open(buffer)
    ela_im = ImageChops.difference(original, compressed)
    
    extrema = ela_im.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    if max_diff == 0:
        max_diff = 1
    scale_factor = 255.0 / max_diff
    return ImageEnhance.Brightness(ela_im).enhance(scale_factor)

# 2. Load the Trained Brain
def load_trained_model():
    model = models.resnet18()
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(128, 2)
    )
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.to(DEVICE)
    model.eval()
    return model

# 3. Predict on Any Image
def predict_image(image_path):
    print("=" * 50)
    print(f"🔍 SCANNING IMAGE: {image_path}")
    print("=" * 50)

    # Transform
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    ela_img = compute_ela(image_path)
    input_tensor = transform(ela_img).unsqueeze(0).to(DEVICE)

    model = load_trained_model()

    with torch.no_grad():
        outputs = model(input_tensor)
        probabilities = torch.softmax(outputs, dim=1)[0]
        confidence, predicted_class = torch.max(probabilities, 0)

    classes = ['AUTHENTIC (GENUINE)', 'FORGED (DIGITALLY TAMPERED)']
    verdict = classes[predicted_class.item()]
    conf_pct = confidence.item() * 100

    if predicted_class.item() == 0:
        print(f"✅ VERDICT: {verdict}")
        print(f"🛡️ Trust Confidence: {conf_pct:.2f}% (Passed ELA Forensics)")
    else:
        print(f"🚨 VERDICT: {verdict}")
        print(f"⚠️ Forgery Probability: {conf_pct:.2f}% (Compression Anomaly Detected)")
    print("=" * 50)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        # Default test from authentic folder
        test_file = "dataset/authentic/Au_ani_0001.jpg"
    
    predict_image(test_file)