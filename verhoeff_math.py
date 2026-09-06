# UIDAI Dihedral Group D5 Multiplication Table (d)
D_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

# Permutation Table (p)
P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

# Inverse Table (inv)
INV_TABLE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def generate_verhoeff(num_str: str) -> str:
    """Generates the 12th Verhoeff check digit for any 11-digit sequence"""
    clean_num = num_str.replace(" ", "").replace("-", "")
    c = 0
    reversed_digits = [int(d) for d in reversed(clean_num)]
    for idx, digit in enumerate(reversed_digits):
        c = D_TABLE[c][P_TABLE[(idx + 1) % 8][digit]]
    check_digit = INV_TABLE[c]
    return clean_num + str(check_digit)

def validate_aadhaar_verhoeff(aadhaar_number: str) -> bool:
    """Validates 12-digit Aadhaar number using Dihedral Group D5 Verhoeff checksum"""
    clean_num = aadhaar_number.replace(" ", "").replace("-", "")
    if len(clean_num) != 12 or not clean_num.isdigit():
        return False

    c = 0
    reversed_digits = [int(d) for d in reversed(clean_num)]
    for idx, digit in enumerate(reversed_digits):
        c = D_TABLE[c][P_TABLE[idx % 8][digit]]

    return c == 0

# Test Run
if __name__ == "__main__":
    print("=" * 55)
    print("🇮🇳 TESTING UIDAI VERHOEFF D5 AADHAAR ALGORITHM")
    print("=" * 55)

    # Generate a mathematically valid 12-digit Aadhaar from prefix '54892109458'
    valid_aadhaar = generate_verhoeff("5489 2109 458")
    formatted_valid = f"{valid_aadhaar[:4]} {valid_aadhaar[4:8]} {valid_aadhaar[8:]}"
    is_valid = validate_aadhaar_verhoeff(formatted_valid)
    
    print(f"1. Genuine Aadhaar Number [{formatted_valid}]:")
    print(f"   Verdict: {'VALID AADHAAR NUMBER ✅ (Satisfies D5 Parity)' if is_valid else 'INVALID ❌'}")

    # Fabricated / Fake Aadhaar Number
    fake_aadhaar = "9988 7766 5544"
    is_fake_valid = validate_aadhaar_verhoeff(fake_aadhaar)
    print(f"\n2. Fake Fabricated Number [{fake_aadhaar}]:")
    print(f"   Verdict: {'VALID ✅' if is_fake_valid else 'COUNTERFEIT NUMBER DETECTED 🚨 (Failed Dihedral Parity)'}")
    print("=" * 55)