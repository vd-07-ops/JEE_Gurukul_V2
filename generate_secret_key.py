import secrets

# Generate a secure random key
secret_key = secrets.token_hex(32)
print("\nYour Flask Secret Key:")
print("-" * 50)
print(secret_key)
print("-" * 50)
print("\nAdd this to your .env file as:")
print(f"SECRET_KEY={secret_key}") 