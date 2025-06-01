from datetime import timedelta, timezone, datetime

from cryptography.fernet import Fernet
import jwt
from fastapi import HTTPException
from passlib.context import CryptContext

from src.config import settings


class AuthService:
    password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    fernet = Fernet(settings.FERNET_SECRET_KEY)

    def verify_password(self, plain_password, hashed_password):
        return self.password_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode |= ({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    def get_hash_password(self, password: str) -> str:
        return self.password_context.hash(password)

    def decode_jwt_token(self, jwt_token: str) -> dict:
        try:
            return jwt.decode(jwt_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except jwt.exceptions.DecodeError:
            raise HTTPException(status_code=401, detail="Неверный токен")
        except jwt.exceptions.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Старый токен")

    def encrypt_data(self, data: str) -> str:
        """
        Encrypts the given plaintext and returns a URL-safe Base64 token.
        """
        _data = self.fernet.encrypt(data.encode())
        return _data.decode()

    def decrypt_data(self, data: str) -> str:
        """
        Decrypts the Fernet token back to the original plaintext.
        Raises InvalidToken if the key/token is wrong or data was tampered.
        """
        _data = self.fernet.decrypt(data.encode())
        return _data.decode()
