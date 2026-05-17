#!/usr/bin/env python3

'''
# OSEP -- Encryptor.py

A flexible XOR + AES (AES-256-CTR) encryptor for shellcode, payloads, or strings — designed for use in offensive security, including OSEP-level scenarios.

## Features
- XOR or AES-256-CTR encryption
- Input from file or string
- Output formats: raw bytes, hex string, C array, PowerShell array, C# array
- Random key generation
- Auto SHA-256 key derivation for AES
- Simple decryption stub suggestion for XOR (C)

## Requirements
- Python 3
- `pycryptodome` (`pip install pycryptodome`)

## Example Usage

### XOR with random key, C array output
python3 encryptor.py --mode xor --input shellcode.bin --randkey 16 --outfmt carray --output encrypted.c

### AES with passphrase key, hex output
python3 encryptor.py --mode aes --string "HelloWorld" --key SuperSecret123 --outfmt hex

### PowerShell array output
python3 encryptor.py --mode xor --input shellcode.bin --key myXORkey --outfmt psarray --output payload.ps1


'''

import argparse
import os
import random
import string
import hashlib
from Crypto.Cipher import AES

def random_key(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def xor_encrypt(data, key):
    key_bytes = key.encode()
    return bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data)])

def aes_encrypt(data, key):
    key_hashed = hashlib.sha256(key.encode()).digest()
    nonce = os.urandom(8)
    cipher = AES.new(key_hashed, AES.MODE_CTR, nonce=nonce)
    ciphertext = cipher.encrypt(data)
    return nonce + ciphertext

def format_bytes(data, outfmt):
    if outfmt == "raw":
        return data
    elif outfmt == "hex":
        return data.hex()
    elif outfmt == "carray":
        return "unsigned char buf[] = {" + ', '.join(f"0x{b:02x}" for b in data) + "};"
    elif outfmt == "psarray":
        return "[Byte[]] $buf = " + ','.join(f"0x{b:02x}" for b in data)
    elif outfmt == "csarray":
        return "byte[] buf = new byte[] { " + ', '.join(f"0x{b:02x}" for b in data) + " };"
    else:
        raise ValueError("Unsupported output format")

def generate_stub(mode, key, extra=None):
    if mode == "xor":
        return f"// XOR decryption stub example (C)\n" + \
               f"for(int i=0;i<sizeof(buf);i++) buf[i]^='{key}';"
    elif mode == "aes":
        return "// AES decryption stub not trivial to generate. Document key and nonce used."
    return ""

def main():
    parser = argparse.ArgumentParser(description="XOR / AES Encryptor for Shellcode/Files")
    parser.add_argument("--mode", required=True, choices=["xor", "aes"], help="Encryption mode")
    parser.add_argument("--input", help="Input file")
    parser.add_argument("--string", help="Input string instead of file")
    parser.add_argument("--key", help="Encryption key")
    parser.add_argument("--randkey", type=int, help="Generate random key of specified length")
    parser.add_argument("--outfmt", required=True, choices=["raw", "hex", "carray", "psarray", "csarray"], help="Output format")
    parser.add_argument("--output", help="Output file")
    args = parser.parse_args()

    if not args.input and not args.string:
        parser.error("Must specify --input file or --string data")

    if args.randkey:
        key = random_key(args.randkey)
        print(f"[+] Generated random key: {key}")
    elif args.key:
        key = args.key
    else:
        parser.error("Must specify --key or --randkey")

    if args.input:
        with open(args.input, "rb") as f:
            data = f.read()
    else:
        data = args.string.encode()

    if args.mode == "xor":
        encrypted = xor_encrypt(data, key)
    elif args.mode == "aes":
        encrypted = aes_encrypt(data, key)

    formatted = format_bytes(encrypted, args.outfmt)

    if args.output:
        if args.outfmt == "raw":
            with open(args.output, "wb") as f:
                f.write(encrypted)
        else:
            with open(args.output, "w") as f:
                f.write(formatted)
    else:
        print(formatted)

    print("\n[+] Decryption stub suggestion:")
    print(generate_stub(args.mode, key))

if __name__ == "__main__":
    main()
