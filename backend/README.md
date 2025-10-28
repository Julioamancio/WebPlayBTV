# WebPlay Backend (FastAPI)

Backend mínimo com FastAPI e rota de saúde (`/health`).

## Executar localmente

1. Crie o ambiente virtual:
   ```powershell
   python -m venv .venv
   ```

2. Instale as dependências (sem precisar ativar o venv):
   ```powershell
   .\.venv\Scripts\python -m pip install -r requirements.txt
   ```

3. Rode o servidor de desenvolvimento:
   ```powershell
   .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
   ```

4. Verifique:
   - Health: http://localhost:8000/health

## Autenticação (JWT) — Endpoints

- Login:
  ```powershell
  $body = '{"username":"admin@example.com","password":"admin123"}'
  Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body $body
  ```
  Resposta: `{ "access_token": "...", "token_type": "bearer" }`

- Perfil atual (`/auth/me`), usando o token obtido no login:
  ```powershell
  $token = (Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}').access_token
  Invoke-RestMethod -Uri http://localhost:8000/auth/me -Headers @{ Authorization = "Bearer $token" }
  ```

- Logout (stateless):
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/auth/logout -Method Post
  ```

Notas:
- Este fluxo usa base de usuários fake em memória e não deve ser usado em produção.
- Configure um `SECRET_KEY` via `.env` para tokens mais seguros.

## Dispositivos (SQLModel)

- Banco: SQLite local em `backend/webplay.db` (criado automaticamente no startup).
- Registrar dispositivo do usuário atual:
  ```powershell
  $token = (Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}').access_token
  $body = '{"fingerprint":"device-abc-123","name":"Meu PC","platform":"Windows 11"}'
  Invoke-RestMethod -Uri http://localhost:8000/devices/register -Method Post -ContentType 'application/json' -Body $body -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```

- Listar seus dispositivos:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/devices/me -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```

Notas:
- O registro é idempotente por `fingerprint` + usuário: se já existir, retorna o mesmo registro.
- Modelos básicos em `app/models.py` (User, Device, License) — em breve conectaremos com usuários persistentes.

## Observabilidade e Métricas

- Endpoint Prometheus:
  - `GET http://localhost:8000/metrics` (formato `text/plain; version=0.0.4`)
- Middleware coleta automaticamente:
  - `http_requests_total{method, path, status}`
  - `http_request_duration_seconds{method, path, status}` com buckets padrões
- `X-Request-ID`:
  - Header incluído em todas as respostas; pode ser enviado no request para propagar o mesmo ID.

Como testar (PowerShell):
```powershell
Invoke-RestMethod -Uri http://localhost:8000/health -Headers @{ 'X-Request-ID' = 'test-123' } -Method Get | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/metrics -Method Get | Select-Object -First 40
```

## Catálogo EPG (XMLTV)

- Variável de ambiente: `EPG_SOURCE`
  - Aceita caminho relativo no diretório `backend` (ex.: `sample.xml`) ou URL (ex.: `https://.../epg.xml`)
  - Padrão: `sample.xml` (arquivo de exemplo incluso)
- Endpoints:
  - `GET /catalog/epg` — retorna canais e a grade completa normalizada
  - `GET /catalog/epg/{channel_id}` — retorna dados do canal e sua programação
    - Query opcionais: `start`, `end` (ambos ISO8601). Se o timezone for omitido, assume UTC.
    - O filtro retorna programas que tenham sobreposição com o intervalo informado. Se apenas `start` for informado, retorna do instante em diante. Se apenas `end` for informado, retorna até o instante.
- Cache: o XMLTV é armazenado em cache por 5 minutos para reduzir I/O e latência

Como testar (PowerShell):
```powershell
# EPG local (padrão usa backend/sample.xml)
Invoke-RestMethod -Uri http://localhost:8000/catalog/epg -Method Get | ConvertTo-Json -Depth 4 | Out-Host
Invoke-RestMethod -Uri http://localhost:8000/catalog/epg/jctv -Method Get | ConvertTo-Json -Depth 4 | Out-Host

# Filtro temporal por canal (intervalo)
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg/jctv?start=2025-01-01T08:30:00Z&end=2025-01-01T10:00:00Z" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

# Apenas a partir de um instante
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg/jctv?start=2025-01-01T09:00:00Z" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

# Apenas até um instante
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg/jctv?end=2025-01-01T08:59:00Z" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

# Usar um EPG remoto (exemplo)
$env:EPG_SOURCE = 'https://example.com/epg.xml'
Invoke-RestMethod -Uri http://localhost:8000/catalog/epg -Method Get | Select-Object -First 1 | Out-Host
```

Formato de resposta resumido:
```json
{
  "channels": {
    "<channel_id>": { "id": "<id>", "name": "<display>", "icon": "<url>" }
  },
  "programs": {
    "<channel_id>": [ { "title": "...", "description": "...", "start": "iso8601", "stop": "iso8601" } ]
  }
}
```

## Catálogo M3U e Enriquecimento

- Variável de ambiente: `M3U_SOURCE`
  - Aceita caminho relativo no diretório `backend` (ex.: `sample.m3u`) ou URL
  - Padrão: `sample.m3u` (arquivo de exemplo incluso)
- Endpoints:
  - `GET /catalog/m3u` — retorna o conteúdo bruto do M3U
  - `GET /catalog/channels` — lista os canais parseados do M3U
  - `GET /catalog/channels/enriched` — canais do M3U enriquecidos com metadados do EPG
  - `GET /catalog/now` — para cada canal, programa atual e próximo (se houver)
    - Query opcional: `time` (ISO8601). Se o timezone for omitido, assume UTC.

Observações:
- A associação M3U ↔ EPG é feita por `tvg-id` (M3U) e `channel.id` (XMLTV) com comparação case-insensitive (por exemplo, `JCTV` ↔ `jctv`).
- O endpoint `/catalog/now` usa o horário atual do servidor; se a grade do XMLTV estiver fora da faixa atual, `current` e/ou `next` podem ser `null`.

Como testar (PowerShell):
```powershell
# Canais parseados do M3U
Invoke-RestMethod -Uri http://localhost:8000/catalog/channels -Method Get | ConvertTo-Json -Depth 3 | Out-Host

# Canais enriquecidos com EPG
Invoke-RestMethod -Uri http://localhost:8000/catalog/channels/enriched -Method Get | ConvertTo-Json -Depth 4 | Out-Host

# Programação atual e próxima
Invoke-RestMethod -Uri http://localhost:8000/catalog/now -Method Get | ConvertTo-Json -Depth 5 | Out-Host

# Consultar a programação considerando um instante específico (útil para samples estáticos)
Invoke-RestMethod -Uri "http://localhost:8000/catalog/now?time=2025-01-01T08:30:00Z" -Method Get | ConvertTo-Json -Depth 6 | Out-Host
```
