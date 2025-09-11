from cryptography.fernet import Fernet

def generate_key():
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file:
        key_file.write(key)

def encrypt_price(price):
    with open("secret.key", "rb") as key_file:
        key = key_file.read()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(price.encode())
    with open("pricing.json", "wb") as f:
        f.write(encrypted)

if __name__ == "__main__":
    generate_key()
    encrypt_price("App Price: $2.99")
    print("Pricing encrypted successfully!")
