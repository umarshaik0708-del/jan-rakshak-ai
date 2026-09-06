"""
Jan Rakshak AI - National Forensic Document OCR & Identity Parsing Engine
========================================================================
Supports:
1. Indian Aadhaar Card (12-digit UID extraction + UIDAI Verhoeff Checksum)
2. International & Indian Passports (ICAO Doc 9303 MRZ extraction + 7-3-1 Checksum)
3. Indian PAN Cards (10-digit Alphanumeric Structure + Entity Validation)
"""

import re
import cv2
import numpy as np
import easyocr
import torch
from PIL import Image
from verhoeff_math import validate_aadhaar_verhoeff
from mrz_math import parse_and_verify_mrz_td3

import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Initialize EasyOCR Reader with GPU if available
USE_GPU = torch.cuda.is_available()
_reader = None

def get_reader():
    global _reader
    if _reader is None:
        print(f"[INFO] Initializing EasyOCR Engine (GPU={USE_GPU})...")
        _reader = easyocr.Reader(['en'], gpu=USE_GPU, verbose=False)
    return _reader

def extract_aadhaar_details(text_lines):
    """
    Extracts 12-digit Aadhaar UID, Name, DOB, Gender and verifies against Dihedral D5 Verhoeff algorithm.
    """
    raw_texts = [t[1].strip() for t in text_lines if t[1].strip()]
    full_text = " ".join(raw_texts)
    
    # Look for 4 4 4 digit pattern or 12 continuous digits
    aadhaar_pattern = r'\b\d{4}\s?\d{4}\s?\d{4}\b'
    matches = re.findall(aadhaar_pattern, full_text)
    
    uid_found = None
    is_valid_verhoeff = False
    
    for match in matches:
        clean_num = match.replace(" ", "").strip()
        if len(clean_num) == 12:
            uid_found = clean_num
            is_valid_verhoeff = validate_aadhaar_verhoeff(clean_num)
            if is_valid_verhoeff:
                break
                
    # Extract DOB/Year of Birth
    dob = None
    dob_match = re.search(r'(?:DOB|D\.O\.B|Birth|Year of Birth|పుట్టిన తేదీ|जन्म तिथि|जन्म वर्ष)[:\s/]*([0-9]{2}[/-][0-9]{2}[/-][0-9]{4}|(?:19|20)[0-9]{2})', full_text, re.IGNORECASE)
    if dob_match:
        dob = dob_match.group(1).replace("-", "/")
    
    if not dob:
        date_match = re.search(r'\b([0-3][0-9]/[0-1][0-9]/(?:19|20)[0-9]{2})\b', full_text)
        if date_match:
            dob = date_match.group(1)
            
    # Extract Gender
    gender = None
    g_match = re.search(r'\b(MALE|FEMALE|TRANSGENDER|పురుషుడు|महिला|पुरुष)\b', full_text, re.IGNORECASE)
    if g_match:
        g_raw = g_match.group(1).lower()
        gender = "MALE" if any(w in g_raw for w in ["male", "పురుషుడు", "पुरुष"]) else ("FEMALE" if any(w in g_raw for w in ["female", "మహిళ", "महिला"]) else "TRANSGENDER")
        
    # Extract English Name
    name = None
    stop_words = ["GOVERNMENT", "INDIA", "AADHAAR", "MALE", "FEMALE", "DOB", "YEAR", "ENROLMENT", "HELP", "UIDAI", "PROOF", "IDENTITY", "CITIZENSHIP", "SCANNING", "OFFLINE", "COMPLETE", "CAMERA", "UPLOAD", "LIVE"]
    for t in raw_texts:
        clean_t = re.sub(r'[^A-Za-z\s]', '', t).strip()
        words = clean_t.split()
        if 2 <= len(words) <= 4 and all(len(w) >= 2 for w in words):
            if not any(sw in clean_t.upper() for sw in stop_words):
                name = clean_t.upper()
                break
                
    return {
        "doc_type": "Aadhaar Card",
        "doc_number": uid_found,
        "name": name,
        "is_checksum_valid": is_valid_verhoeff,
        "checksum_type": "Verhoeff D5 Checksum",
        "dob": dob,
        "gender": gender,
        "status": "VALID_DOCUMENT" if (uid_found and is_valid_verhoeff) else "SUSPICIOUS_OR_INVALID"
    }

def extract_passport_details(text_lines):
    """
    Extracts 2-line ICAO Doc 9303 MRZ from Passports and verifies 7-3-1 weight matrix.
    """
    raw_strings = [t[1].upper().replace(" ", "") for t in text_lines]
    
    # Find MRZ lines (typically contain '<' and are ~44 chars or start with P<)
    mrz_candidates = []
    for s in raw_strings:
        if "<" in s or s.startswith("P<") or s.startswith("P"):
            clean_line = s.replace(" ", "")
            if len(clean_line) >= 30:
                mrz_candidates.append(clean_line)
                
    if len(mrz_candidates) >= 2:
        line1 = mrz_candidates[-2]
        line2 = mrz_candidates[-1]
        
        # Pad or trim to 44 characters if needed
        line1 = line1.ljust(44, '<')[:44]
        line2 = line2.ljust(44, '<')[:44]
        
        mrz_res = parse_and_verify_mrz_td3(line1, line2)
        return {
            "doc_type": "Passport (ICAO 9303)",
            "doc_number": mrz_res.get("passport_number"),
            "mrz_line1": line1,
            "mrz_line2": line2,
            "is_checksum_valid": mrz_res.get("overall_valid", False),
            "checksum_type": "ICAO [7,3,1] Modulo 10 Checksum",
            "name": f"{mrz_res.get('given_names', '')} {mrz_res.get('surname', '')}".strip(),
            "nationality": mrz_res.get("nationality"),
            "dob": mrz_res.get("dob"),
            "expiry": mrz_res.get("expiry"),
            "sex": mrz_res.get("sex"),
            "status": "VALID_DOCUMENT" if mrz_res.get("overall_valid") else "SUSPICIOUS_OR_INVALID"
        }
        
    return {
        "doc_type": "Passport",
        "doc_number": None,
        "is_checksum_valid": False,
        "status": "MRZ_NOT_DETECTED"
    }

def extract_pan_details(text_lines):
    """
    Extracts 10-character Indian Permanent Account Number (PAN) and checks format.
    Format: [A-Z]{5}[0-9]{4}[A-Z]{1}
    4th Char represents Status: P=Individual, C=Company, H=HUF, F=Firm, A=AOP, T=Trust
    """
    full_text = " ".join([t[1] for t in text_lines])
    pan_pattern = r'\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b'
    matches = re.findall(pan_pattern, full_text.upper())
    
    pan_found = matches[0] if matches else None
    is_valid = False
    entity_type = "Unknown"
    
    if pan_found:
        is_valid = True
        status_char = pan_found[3]
        status_map = {
            'P': 'Individual / Person',
            'C': 'Company',
            'H': 'Hindu Undivided Family (HUF)',
            'F': 'Partnership Firm',
            'A': 'Association of Persons (AOP)',
            'T': 'Trust',
            'B': 'Body of Individuals (BOI)',
            'L': 'Local Authority',
            'J': 'Artificial Juridical Person',
            'G': 'Government Agency'
        }
        entity_type = status_map.get(status_char, "Special Entity")
        
    return {
        "doc_type": "Income Tax PAN Card",
        "doc_number": pan_found,
        "is_checksum_valid": is_valid,
        "checksum_type": "Income Tax Department Structure Check",
        "entity_type": entity_type,
        "status": "VALID_DOCUMENT" if is_valid else "SUSPICIOUS_OR_INVALID"
    }

def process_document_ocr(image_input):
    """
    Main entry point for OCR & Automated Document Identification.
    Accepts PIL Image, file path, or OpenCV numpy array.
    """
    if isinstance(image_input, Image.Image):
        cv_img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, str):
        cv_img = cv2.imread(image_input)
    elif isinstance(image_input, np.ndarray):
        cv_img = image_input
    else:
        raise ValueError("Unsupported image format for OCR")

    # Run EasyOCR
    reader = get_reader()
    results = reader.readtext(cv_img)
    
    # Structure text items
    detected_texts = []
    full_corpus = ""
    for bbox, text, conf in results:
        detected_texts.append({
            "text": text,
            "confidence": round(float(conf) * 100, 2),
            "bbox": [[int(pt[0]), int(pt[1])] for pt in bbox]
        })
        full_corpus += f" {text}"

    corpus_upper = full_corpus.upper()
    
    # Auto-detect document class
    if any(k in corpus_upper for k in ["PASSPORT", "REPUBLIC OF INDIA", "<<<", "P<IND"]):
        doc_analysis = extract_passport_details(results)
    elif any(k in corpus_upper for k in ["AADHAAR", "UIDAI", "GOVERNMENT OF INDIA", "MERA AADHAAR", "DOB", "YEAR OF BIRTH"]) or re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', full_corpus):
        doc_analysis = extract_aadhaar_details(results)
    elif any(k in corpus_upper for k in ["INCOME TAX", "PERMANENT ACCOUNT NUMBER", "FATHER'S NAME", "SIGNATURE", "INCOMETAX"]):
        doc_analysis = extract_pan_details(results)
    else:
        # Fallback: check all three
        aadhaar_try = extract_aadhaar_details(results)
        if aadhaar_try["doc_number"]:
            doc_analysis = aadhaar_try
        else:
            pan_try = extract_pan_details(results)
            if pan_try["doc_number"]:
                doc_analysis = pan_try
            else:
                doc_analysis = {
                    "doc_type": "Unknown Document",
                    "doc_number": None,
                    "is_checksum_valid": False,
                    "status": "UNRECOGNIZED_DOCUMENT_TYPE"
                }

    return {
        "classification": doc_analysis,
        "detected_boxes_count": len(detected_texts),
        "raw_text_extracted": [t["text"] for t in detected_texts],
        "average_ocr_confidence": round(float(np.mean([t["confidence"] for t in detected_texts])), 2) if detected_texts else 0.0
    }

if __name__ == "__main__":
    from verhoeff_math import generate_verhoeff
    
    print("=" * 65)
    print("[OCR] TESTING JAN RAKSHAK MULTI-DOCUMENT OCR & PARSING ENGINE")
    print("=" * 65)

    # 1. Test Aadhaar Card
    val_aadhaar = generate_verhoeff("5489 2109 458")
    aadhaar_canvas = np.ones((200, 600, 3), dtype=np.uint8) * 255
    cv2.putText(aadhaar_canvas, "GOVERNMENT OF INDIA", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(aadhaar_canvas, "DOB: 15/04/1996  MALE", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(aadhaar_canvas, f"{val_aadhaar[:4]} {val_aadhaar[4:8]} {val_aadhaar[8:]}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    
    res1 = process_document_ocr(aadhaar_canvas)
    print("\n1. AADHAAR CARD EXTRACTION:")
    print(f"   Detected Type: {res1['classification']['doc_type']}")
    print(f"   UID: {res1['classification']['doc_number']} | Checksum Valid: {res1['classification']['is_checksum_valid']}")
    print(f"   DOB: {res1['classification'].get('dob')} | Gender: {res1['classification'].get('gender')}")
    print(f"   Status: {res1['classification']['status']}")

    # 2. Test Passport MRZ
    passport_canvas = np.ones((200, 900, 3), dtype=np.uint8) * 255
    cv2.putText(passport_canvas, "PASSPORT REPUBLIC OF INDIA", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(passport_canvas, "P<INDSHAIK<<UMAR<<<<<<<<<<<<<<<<<<<<<<<<<<<", (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(passport_canvas, "P8920194<8IND9604157M3108099<<<<<<<<<<<<<<<2", (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    res2 = process_document_ocr(passport_canvas)
    print("\n2. PASSPORT MRZ EXTRACTION:")
    print(f"   Detected Type: {res2['classification']['doc_type']}")
    print(f"   Passport No: {res2['classification']['doc_number']} | Name: {res2['classification'].get('name')}")
    print(f"   Nationality: {res2['classification'].get('nationality')} | DOB: {res2['classification'].get('dob')} | Exp: {res2['classification'].get('expiry')}")
    print(f"   MRZ Valid: {res2['classification']['is_checksum_valid']} | Status: {res2['classification']['status']}")

    # 3. Test PAN Card
    pan_canvas = np.ones((200, 600, 3), dtype=np.uint8) * 255
    cv2.putText(pan_canvas, "INCOME TAX DEPARTMENT", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(pan_canvas, "PERMANENT ACCOUNT NUMBER", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(pan_canvas, "ABCDE1234F", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    
    res3 = process_document_ocr(pan_canvas)
    print("\n3. PAN CARD EXTRACTION:")
    print(f"   Detected Type: {res3['classification']['doc_type']}")
    print(f"   PAN Number: {res3['classification']['doc_number']} | Entity Type: {res3['classification'].get('entity_type')}")
    print(f"   Valid: {res3['classification']['is_checksum_valid']} | Status: {res3['classification']['status']}")
    print("=" * 65)
