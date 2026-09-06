import os
from PIL import Image

# Folder paths
AUTH_DIR = "dataset/authentic"
FORG_DIR = "dataset/forged"

def inspect_dataset():
    print("=" * 45)
    print("🔍 JAN RAKSHAK AI — DATASET INSPECTION")
    print("=" * 45)

    # 1. Count Authentic Images
    auth_files = [f for f in os.listdir(AUTH_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif'))] if os.path.exists(AUTH_DIR) else []
    print(f"✅ Authentic Images Found: {len(auth_files)}")

    # 2. Count Forged Images
    forg_files = [f for f in os.listdir(FORG_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif'))] if os.path.exists(FORG_DIR) else []
    print(f"🚨 Forged/Tampered Images Found: {len(forg_files)}")

    # 3. Check an example image size
    if auth_files:
        sample_path = os.path.join(AUTH_DIR, auth_files[0])
        with Image.open(sample_path) as img:
            print(f"\n🖼️ Sample Authentic Image: {auth_files[0]}")
            print(f"   Resolution: {img.size[0]}x{img.size[1]} pixels | Mode: {img.mode}")

    if forg_files:
        sample_path = os.path.join(FORG_DIR, forg_files[0])
        with Image.open(sample_path) as img:
            print(f"🖼️ Sample Forged Image: {forg_files[0]}")
            print(f"   Resolution: {img.size[0]}x{img.size[1]} pixels | Mode: {img.mode}")

    print("=" * 45)
    if len(auth_files) > 0 and len(forg_files) > 0:
        print("🎉 Dataset verified successfully! Ready for training pipeline.")
    else:
        print("⚠️ Warning: One of your folders is empty. Please add images.")

if __name__ == "__main__":
    inspect_dataset()