# WebPlay BTV

Projeto dividido em backend (FastAPI) e frontend estático. O backend serve o painel em `/app/index.html`, expõe APIs de autenticação/licenciamento e inclui um proxy para playlists M3U.

## Backend (FastAPI)

Local: `backend/`

### Rodando localmente (Windows PowerShell)

```powershell
cd c:\Users\julio.amancio\Documents\Web\WebPlayBTV\backend
.\scripts\run_dev.ps1
```

O script cria/usa `.venv`, instala `requirements.txt`, aplica migrações (`alembic upgrade head`) e inicia o `uvicorn` com reload. Para evitar reinstalar dependências use `.\scripts\run_dev.ps1 -SkipInstall`.

Endpoints úteis:

- Health: `http://localhost:8000/health`
- Frontend via backend: `http://localhost:8000/app/index.html`

### Migrações com Alembic

Configurações vivem em `backend/.env` (copie de `.env.example`).

> ⚠️ Defina um `JWT_SECRET` forte ao configurar o `.env`. O backend valida os segredos no startup e só permite o valor de placeholder caso `ALLOW_INSECURE_DEFAULTS=1` esteja definido (uso local apenas).

Gerar nova revisão:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic revision -m "sua mensagem"
```

Aplicar revisões:

```powershell
alembic upgrade head
```

### Estrutura principal

- `app/core`: configuração e utilitários (p.ex. segurança)
- `app/db`: sessão SQLAlchemy e integração com Alembic
- `app/models`: modelos ORM
- `app/schemas`: modelos Pydantic
- `app/services`: regras de negócio reutilizáveis (auth, audit, m3u, streaming)
- `app/api/routes`: rotas FastAPI separadas por domínio
- `scripts`: automação (`run_dev.ps1`, `run_dev.sh`)
- `alembic`: migrações versionadas

### Próximos passos (backend)

- Integração Stripe (Checkout + Webhooks)
- Harden de segurança (restringir CORS, rate limiting, tokens seguros)
- Observabilidade (logs estruturados, métricas)

## Frontend (estático por enquanto)

Local: `frontend/`

Planejado migrar para React/Vite + TypeScript. Enquanto isso, `index.html` concentra o painel administrativo e consome a API diretamente.

### Próximos passos (frontend)

- Criar projeto Vite/React conforme plano inicial
- Componentizar telas de login, dashboard, catálogo e planos
- Aplicar proteção de rotas e armazenamento seguro de credenciais
- Evoluir para PWA com cache controlado
