import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ========== FROM LAB 2 ==========
    APP_NAME: str = os.getenv("APP_NAME", "FastAPI Auth Lab 3")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # ========== UPDATED IN LAB 3 ==========
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

    # ========== NEW IN LAB 3 ==========
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


settings = Settings()