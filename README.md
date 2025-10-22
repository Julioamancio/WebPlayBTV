# WebPlay BTV

Estrutura inicial do projeto.

## Backend (FastAPI)

Local: `backend/`

### Rodando localmente (Windows PowerShell)

1. Criar venv e instalar deps (já feito):
   ```powershell
   cd c:\Users\julio.amancio\Documents\Web_Player
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install fastapi "uvicorn[standard]"
   ```

2. Iniciar servidor:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Testar:
   - Health: `http://localhost:8000/health`
   - Root: `http://localhost:8000/`

### Próximos passos (backend)
- Modelos e DB (PostgreSQL + SQLAlchemy + Alembic)
- Auth JWT (registro/login/refresh)
- Integração Stripe (Checkout + Webhooks)

## Frontend (React + Vite + TS)

Local: `frontend/`

### Criar projeto (quando for possível rodar comandos)
```powershell
cd c:\Users\julio.amancio\Documents\Web_Player
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm run dev
```

Abrir: `http://localhost:5173/`

### Próximos passos (frontend)
- Páginas: Login/Registro, Planos/Checkout, Dashboard, Catálogo
- Integração com API e proteção de rotas
- PWA (cache controlado)