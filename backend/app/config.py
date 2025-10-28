import os
from dotenv import load_dotenv


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# TTLs de cache (segundos)
EPG_TTL_SECONDS = float(os.getenv("EPG_TTL_SECONDS", "300"))
M3U_TTL_SECONDS = float(os.getenv("M3U_TTL_SECONDS", "300"))

# Retries para fontes remotas
EPG_FETCH_RETRIES = int(os.getenv("EPG_FETCH_RETRIES", "3"))
M3U_FETCH_RETRIES = int(os.getenv("M3U_FETCH_RETRIES", "3"))
FETCH_BACKOFF_SECONDS = float(os.getenv("FETCH_BACKOFF_SECONDS", "0.5"))
