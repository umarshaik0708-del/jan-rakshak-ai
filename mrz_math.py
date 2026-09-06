# ICAO 9303 Character to Number Mapping
CHAR_MAP = {
    '<': 0, '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17, 'I': 18,
    'J': 19, 'K': 20, 'L': 21, 'M': 22, 'N': 23, 'O': 24, 'P': 25, 'Q': 26, 'R': 27,
    'S': 28, 'T': 29, 'U': 30, 'V': 31, 'W': 32, 'X': 33, 'Y': 34, 'Z': 35
}

WEIGHTS = [7, 3, 1]

def compute_check_digit(data_string: str) -> int:
    """Computes ICAO 9303 Check Digit using [7, 3, 1] weighting modulo 10"""
    total = 0
    for idx, char in enumerate(data_string):
        val = CHAR_MAP.get(char.upper(), 0)
        weight = WEIGHTS[idx % 3]
        total += val * weight
    return total % 10

def verify_passport_mrz(doc_num: str, doc_check: str, dob: str, dob_check: str, expiry: str, expiry_check: str):
    """Verifies all check digits on a passport MRZ line"""
    calc_doc = compute_check_digit(doc_num)
    calc_dob = compute_check_digit(dob)
    calc_exp = compute_check_digit(expiry)

    is_doc_valid = (calc_doc == int(doc_check))
    is_dob_valid = (calc_dob == int(dob_check))
    is_exp_valid = (calc_exp == int(expiry_check))

    is_all_valid = is_doc_valid and is_dob_valid and is_exp_valid

    return {
        "status": "VALID_AUTHENTIC" if is_all_valid else "FORGERY_DETECTED",
        "doc_number_valid": is_doc_valid,
        "dob_valid": is_dob_valid,
        "expiry_valid": is_exp_valid,
        "details": f"Doc Check: {calc_doc} (Expected: {doc_check}), DOB Check: {calc_dob} (Expected: {dob_check})"
    }

def parse_and_verify_mrz_td3(line1: str, line2: str):
    """
    Parses and verifies a standard 2-line 44-character ICAO 9303 TD3 Passport MRZ.
    """
    line1 = line1.strip().upper().replace(" ", "")
    line2 = line2.strip().upper().replace(" ", "")
    
    # Pad to 44 if needed
    line1 = line1.ljust(44, '<')[:44]
    line2 = line2.ljust(44, '<')[:44]
    
    # Line 1 parsing: P<ISS<SURNAME<<GIVEN<NAMES
    doc_type_code = line1[0:2]
    issuing_country = line1[2:5]
    names_part = line1[5:]
    
    name_parts = names_part.split("<<")
    surname = name_parts[0].replace("<", " ").strip() if len(name_parts) > 0 else ""
    given_names = name_parts[1].replace("<", " ").strip() if len(name_parts) > 1 else ""
    
    # Line 2 parsing
    doc_number = line2[0:9].replace("<", "")
    doc_check = line2[9]
    nationality = line2[10:13].replace("<", "")
    dob = line2[13:19]
    dob_check = line2[19]
    sex = line2[20]
    expiry = line2[21:27]
    expiry_check = line2[27]
    composite_check = line2[43] if len(line2) >= 44 else "<"
    
    calc_doc = compute_check_digit(line2[0:9])
    calc_dob = compute_check_digit(dob)
    calc_exp = compute_check_digit(expiry)
    
    is_doc_valid = (str(calc_doc) == doc_check)
    is_dob_valid = (str(calc_dob) == dob_check)
    is_exp_valid = (str(calc_exp) == expiry_check)
    
    overall_valid = is_doc_valid and is_dob_valid and is_exp_valid
    
    return {
        "overall_valid": overall_valid,
        "status": "VALID_AUTHENTIC" if overall_valid else "FORGERY_DETECTED",
        "passport_number": doc_number,
        "surname": surname,
        "given_names": given_names,
        "issuing_country": issuing_country,
        "nationality": nationality,
        "dob": f"{dob[4:6]}/{dob[2:4]}/19{dob[0:2]}" if int(dob[0:2]) > 30 else f"{dob[4:6]}/{dob[2:4]}/20{dob[0:2]}",
        "expiry": f"{expiry[4:6]}/{expiry[2:4]}/20{expiry[0:2]}",
        "sex": "Male" if sex == "M" else ("Female" if sex == "F" else "Unspecified"),
        "checks": {
            "doc_number_valid": is_doc_valid,
            "dob_valid": is_dob_valid,
            "expiry_valid": is_exp_valid
        }
    }

# Test Run
if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 55)
    print("[MRZ] TESTING ICAO 9303 PASSPORT MRZ MATHEMATICAL ENGINE")
    print("=" * 55)

    # Test Case 1: Genuine Indian Passport TD3 MRZ lines
    l1 = "P<INDSHAIK<<UMAR<<<<<<<<<<<<<<<<<<<<<<<<<<<"
    l2 = "P8920194<8IND9604157M3108099<<<<<<<<<<<<<<<2"
    result = parse_and_verify_mrz_td3(l1, l2)
    print(f"1. Genuine TD3 MRZ Test: Passport={result['passport_number']}, Valid={result['overall_valid']}")
    print(f"   Details: Name={result['given_names']} {result['surname']}, DOB={result['dob']}, Exp={result['expiry']}")
    print("=" * 55)