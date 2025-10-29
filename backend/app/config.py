import os
from dotenv import load_dotenv


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
# Refresh tokens: expiração em dias (padrão: 14)
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))

# TTLs de cache (segundos)
EPG_TTL_SECONDS = float(os.getenv("EPG_TTL_SECONDS", "300"))
M3U_TTL_SECONDS = float(os.getenv("M3U_TTL_SECONDS", "300"))

# Retries para fontes remotas
EPG_FETCH_RETRIES = int(os.getenv("EPG_FETCH_RETRIES", "3"))
M3U_FETCH_RETRIES = int(os.getenv("M3U_FETCH_RETRIES", "3"))
FETCH_BACKOFF_SECONDS = float(os.getenv("FETCH_BACKOFF_SECONDS", "0.5"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///webplay.db")

# CORS
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")

# Limite opcional: número de dispositivos permitidos por licença ativa
# 0 ou negativo desativa o limite (comportamento atual)
DEVICES_PER_LICENSE = int(os.getenv("DEVICES_PER_LICENSE", "0"))

# Limites por plano de licença (opcional): quando DEVICES_PER_LICENSE > 0,
# este mapa pode sobrescrever o limite por licença conforme o campo `plan` da License.
# Exemplos: bronze=1, silver=2, gold=5. Ajuste conforme sua necessidade.
LICENSE_PLAN_DEVICE_LIMITS = {
    # "bronze": 1,
    # "silver": 2,
    # "gold": 5,
}

# Stripe (opcional)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Rate limiting (opcional)
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() in ("1", "true", "yes")
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_LOGIN_PER_WINDOW = int(os.getenv("RATE_LIMIT_LOGIN_PER_WINDOW", "30"))
RATE_LIMIT_REFRESH_PER_WINDOW = int(os.getenv("RATE_LIMIT_REFRESH_PER_WINDOW", "60"))
RATE_LIMIT_DEVICES_REGISTER_PER_WINDOW = int(os.getenv("RATE_LIMIT_DEVICES_REGISTER_PER_WINDOW", "30"))
