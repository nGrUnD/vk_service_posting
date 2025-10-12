from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_NAME: str
    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASS: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    REDIS_PASSWORD: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int

    FERNET_SECRET_KEY: str

    API_KEY_2CAPTCHA: str

    @property
    def DB_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def SYNC_DB_URL(self):
        # Превращаем asyncpg в sync
        return self.DB_URL.replace('postgresql+asyncpg://', 'postgresql://')



    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()