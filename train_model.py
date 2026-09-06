import os
import io
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import transforms, models
from PIL import Image, ImageChops, ImageEnhance

# --- Training Configuration ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DATASET_DIR = "dataset"
BATCH_SIZE = 16
NUM_EPOCHS = 8          # 8 epochs for deep convergence
LEARNING_RATE = 0.0003
SAVE_PATH = "best_forgery_ela_model.pth"

# 1. Real-Time Error Level Analysis (ELA) Function
def compute_ela(image_path, quality=90, scale=15):
    """Computes compression error difference to highlight digital tampering"""
    original = Image.open(image_path).convert('RGB')
    
    # Save as temporary JPEG with specific compression quality
    buffer = io.BytesIO()
    original.save(buffer, 'JPEG', quality=quality)
    buffer.seek(0)
    compressed = Image.open(buffer)
    
    # Calculate pixel difference (Compression Error Matrix)
    ela_im = ImageChops.difference(original, compressed)
    
    # Scale difference for neural network visibility
    extrema = ela_im.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    if max_diff == 0:
        max_diff = 1
    scale_factor = 255.0 / max_diff
    ela_im = ImageEnhance.Brightness(ela_im).enhance(scale_factor)
    
    return ela_im

# 2. Custom PyTorch Forensic Dataset Loader
class ELADataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.samples = []
        self.transform = transform
        self.classes = ['authentic', 'forged']
        
        auth_dir = os.path.join(root_dir, 'authentic')
        forg_dir = os.path.join(root_dir, 'forged')
        
        if os.path.exists(auth_dir):
            for f in os.listdir(auth_dir):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif')):
                    self.samples.append((os.path.join(auth_dir, f), 0))
                    
        if os.path.exists(forg_dir):
            for f in os.listdir(forg_dir):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif')):
                    self.samples.append((os.path.join(forg_dir, f), 1))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        ela_image = compute_ela(path)
        if self.transform:
            ela_image = self.transform(ela_image)
        return ela_image, label

def train():
    print("=" * 60)
    print(f"🔥 STARTING JAN RAKSHAK ELA FORENSIC TRAINING ON: {DEVICE}")
    print("=" * 60)

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(degrees=10),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    dataset = ELADataset(DATASET_DIR, transform=transform)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_data, val_data = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_data, batch_size=BATCH_SIZE, shuffle=False)

    print(f"📊 Dataset: {len(dataset)} Total Samples ({train_size} Train | {val_size} Validation)")

    # 3. Model: Pretrained ResNet with Fine-tuned Forensic Head
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(128, 2)
    )
    model = model.to(DEVICE)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-3)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.5)

    best_acc = 0.0

    # 4. Training Loop
    for epoch in range(1, NUM_EPOCHS + 1):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        epoch_loss = running_loss / total
        epoch_acc = (correct / total) * 100

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for val_images, val_labels in val_loader:
                val_images, val_labels = val_images.to(DEVICE), val_labels.to(DEVICE)
                val_outputs = model(val_images)
                _, val_preds = torch.max(val_outputs, 1)
                val_total += val_labels.size(0)
                val_correct += (val_preds == val_labels).sum().item()

        val_acc = (val_correct / val_total) * 100
        scheduler.step()

        print(f"Epoch [{epoch:02d}/{NUM_EPOCHS:02d}] | Train Loss: {epoch_loss:.4f} | Train Acc: {epoch_acc:.2f}% | Val Acc: {val_acc:.2f}%")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), SAVE_PATH)
            print(f"  ⭐ High-Accuracy Forensic Model Saved! (Accuracy: {best_acc:.2f}%)")

    print("=" * 60)
    print(f"🎉 Forensic Training Complete! Best Accuracy: {best_acc:.2f}%")
    print(f"💾 Saved to: {SAVE_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    train()