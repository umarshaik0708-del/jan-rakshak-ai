import os
import io
import numpy as np
from PIL import Image, ImageChops

def compute_ela_stats(image_path):
    # 1. Open original image
    original = Image.open(image_path).convert('RGB')
    
    # 2. Recompress in memory at Quality 90
    buffer = io.BytesIO()
    original.save(buffer, 'JPEG', quality=90)
    buffer.seek(0)
    compressed = Image.open(buffer)
    
    # 3. Compute absolute matrix difference: |Original - Compressed|
    diff = ImageChops.difference(original, compressed)
    diff_arr = np.array(diff, dtype=np.float32)
    
    # Return average error and maximum peak error
    return np.mean(diff_arr), np.max(diff_arr)

# Pick first authentic and first forged sample
auth_file = os.listdir('dataset/authentic')[0]
forg_file = os.listdir('dataset/forged')[0]

auth_path = os.path.join('dataset', 'authentic', auth_file)
forg_path = os.path.join('dataset', 'forged', forg_file)

auth_mean, auth_max = compute_ela_stats(auth_path)
forg_mean, forg_max = compute_ela_stats(forg_path)

print('=' * 58)
print('[ELA] ERROR LEVEL ANALYSIS FORENSIC NOISE STATS')
print('=' * 58)
print(f'1. Authentic Image ({auth_file}):')
print(f'   - Mean Compression Error: {auth_mean:.2f}')
print(f'   - Peak Hotspot Residual : {auth_max:.2f}')
print()
print(f'2. Forged / Spliced Image ({forg_file}):')
print(f'   - Mean Compression Error: {forg_mean:.2f}')
print(f'   - Peak Hotspot Residual : {forg_max:.2f}')
print('=' * 58)
