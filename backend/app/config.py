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

# Proxy defaults (opcional)
PROXY_DEFAULT_REFERER = os.getenv("PROXY_DEFAULT_REFERER")
PROXY_DEFAULT_UA = os.getenv("PROXY_DEFAULT_UA")
PROXY_ACCEPT_LANGUAGE = os.getenv("PROXY_ACCEPT_LANGUAGE", "en-US,en;q=0.9")

# Controle de verificação TLS para o proxy (true por padrão)
_verify_raw = os.getenv("PROXY_VERIFY_TLS", "true").strip().lower()
PROXY_VERIFY_TLS = _verify_raw in ("1", "true", "yes", "on")

# Proxy de saída (opcional): define proxies para HTTP/HTTPS
PROXY_OUTBOUND_HTTP = os.getenv("PROXY_OUTBOUND_HTTP")  # ex.: http://user:pass@proxy.local:3128
PROXY_OUTBOUND_HTTPS = os.getenv("PROXY_OUTBOUND_HTTPS")  # ex.: http://user:pass@proxy.local:3128
PROXY_TRUST_ENV = os.getenv("PROXY_TRUST_ENV", "true").strip().lower() in ("1", "true", "yes", "on")
