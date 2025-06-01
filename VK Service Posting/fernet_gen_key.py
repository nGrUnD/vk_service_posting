from cryptography.fernet import Fernet

# Generate a fresh key (do this once and persist it securely!)
key = Fernet.generate_key()
print(key.decode())  # e.g. "gkmT2JKgf0Gf2RmzJ8EA6e5ubOVrj2dI..."
# Save 'key' to a secure place (env var, secrets manager, file with strict perms)