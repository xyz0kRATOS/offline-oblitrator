#!/bin/bash

# Create the keys directory on USB
mkdir -p /media/usb/keys

# Generate a 4096-bit RSA private key
openssl genrsa -out /media/usb/keys/private.pem 4096

# Extract the corresponding public key
openssl rsa -in /media/usb/keys/private.pem -pubout -out /media/usb/keys/public.pem

# Secure file permissions
chmod 600 /media/usb/keys/private.pem
chmod 644 /media/usb/keys/public.pem

echo "✅ RSA key pair generated and stored in /media/usb/keys/"
echo "   - Private key: private.pem (600 permissions)"
echo "   - Public key:  public.pem (644 permissions)"


