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

5. Variáveis de ambiente úteis (via `.env` ou sessão):
   - `SECRET_KEY` — chave JWT
   - `DATABASE_URL` — ex.: `sqlite:///webplay.db` (padrão)
   - `M3U_SOURCE` — ex.: `sample.m3u` ou URL
   - `EPG_SOURCE` — ex.: `sample.xml` ou URL
   - `EPG_TTL_SECONDS`, `M3U_TTL_SECONDS`, `FETCH_BACKOFF_SECONDS`
   - `CORS_ALLOW_ORIGINS` — lista separada por vírgula ou `*`

## Testes automatizados

Para executar a suíte de testes (pytest):

```powershell
cd backend
..\.venv\Scripts\python -m pip install pytest
..\.venv\Scripts\python -m pytest -q
```

## Autenticação (JWT) — Endpoints

- Login:
  ```powershell
  $body = '{"username":"admin@example.com","password":"admin123"}'
  Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body $body
  ```
  Resposta: `{ "access_token": "...", "token_type": "bearer", "refresh_token": "..." }`

### Auditoria de Autenticação

- Os endpoints de autenticação geram eventos de auditoria (`AuditLog`) com correlação via `X-Request-ID`:
  - `auth.login` — criado em login bem-sucedido.
  - `auth.refresh` — criado ao rotacionar o refresh token (single-use); inclui `jti` do token usado.
  - `auth.revoke` — criado ao revogar explicitamente um refresh token; inclui `jti`.
  - `auth.register` — criado ao registrar novo usuário.

- O campo `details` contém informações úteis para diagnóstico, incluindo `request_id` enviado/gerado pelo middleware.

- Consultando seus eventos:
  ```powershell
  $token = (Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}').access_token
  Invoke-RestMethod -Uri http://localhost:8000/audit/me -Headers @{ Authorization = "Bearer $token" }
  ```

- Exemplo de `details`: `status=success request_id=rid-abc-123` ou `rotated=true jti=<uuid> request_id=rid-xyz-456`.

- Login agora retorna também um resumo de capacidade:
  ```powershell
  $login = Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}'
  $token = $login.access_token
  $login.capacity | ConvertTo-Json
  ```
  O login também inclui o header `X-Capacity-Remaining` com o valor atual:
  ```powershell
  $resp = Invoke-WebRequest -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}'
  $resp.Headers["X-Capacity-Remaining"]
  ```
  Campos em `capacity`:
  - `active_licenses`: quantidade de licenças ativas do usuário
  - `devices_per_license`: valor configurado em `DEVICES_PER_LICENSE`
  - `devices_allowed`: total de dispositivos permitidos considerando licenças/plano
  - `devices_count`: dispositivos já registrados pelo usuário
  - `devices_remaining`: quanto ainda pode registrar
  - `limit_enabled`: se regras de limite estão ativas

  Atualização: login também retorna `refresh_token`. Use-o para obter um novo `access_token` quando expirar.

- Renovar token de acesso com refresh token:
  ```powershell
  $login = Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}'
  $refresh = $login.refresh_token
  # Realiza refresh: retorna novo access_token e novo refresh_token
  Invoke-RestMethod -Uri http://localhost:8000/auth/refresh -Method Post -ContentType 'application/json' -Body (ConvertTo-Json @{ refresh_token = $refresh })
  ```
  Resposta: `{ "access_token": "...", "token_type": "bearer", "refresh_token": "..." }`
  
  Configuração:
  - `ACCESS_TOKEN_EXPIRE_MINUTES` — minutos de expiração do JWT de acesso (padrão: 60)
  - `REFRESH_TOKEN_EXPIRE_DAYS` — dias de expiração do refresh token (padrão: 14)

  Rotação e uso único:
  - Ao chamar `POST /auth/refresh`, o refresh token usado é automaticamente revogado (blacklist por `jti`) e um novo `refresh_token` é emitido.
  - Qualquer tentativa de reutilizar o refresh token antigo resultará em `401`.

### Correlação de requisições (X-Request-ID)

- Todas as respostas incluem o cabeçalho `X-Request-ID`.
- Se o cliente enviar `X-Request-ID` na requisição, ele será preservado; caso contrário, um UUID v4 será gerado.
- Utilize esse ID para correlacionar chamadas em logs e troubleshooting.

### Logging estruturado

- O backend emite logs de requisição como linhas JSON com os campos:
  - `method`, `path`, `status`, `duration_ms`, `client_ip`, `request_id`
- Os logs são enviados pelo logger `webplay.request`, facilitando filtragem e análise.
- Combine com `X-Request-ID` para rastrear fluxos entre serviços e identificar problemas rapidamente.

- Revogar refresh token (blacklist):
  ```powershell
  $login = Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}'
  $refresh = $login.refresh_token
  Invoke-RestMethod -Uri http://localhost:8000/auth/revoke -Method Post -ContentType 'application/json' -Body (ConvertTo-Json @{ refresh_token = $refresh })
  ```
  Após a revogação, `POST /auth/refresh` com o mesmo token retornará `401`.

Notas de segurança:
- Os refresh tokens incluem um `jti` único e são validados contra uma blacklist na tabela `RevokedToken`.
- Em caso de comprometimento, revogue o token imediatamente e peça novo login ao usuário.

### Rate limiting (opcional)

- Proteções de abuso para rotas críticas:
  - `/auth/login` — limite por janela
  - `/auth/refresh` — limite por janela
  - `/devices/register` — limite por janela

- Variáveis de ambiente:
  - `RATE_LIMIT_ENABLED` — habilita o middleware (padrão: `false`)
  - `RATE_LIMIT_WINDOW_SECONDS` — tamanho da janela (padrão: `60`)
  - `RATE_LIMIT_LOGIN_PER_WINDOW` — máximo de requisições de login por IP/rota dentro da janela (padrão: `30`)
  - `RATE_LIMIT_REFRESH_PER_WINDOW` — máximo de requisições de refresh por IP/rota dentro da janela (padrão: `60`)
  - `RATE_LIMIT_DEVICES_REGISTER_PER_WINDOW` — máximo de registros de dispositivos por IP/rota dentro da janela (padrão: `30`)

- Métrica Prometheus:
  - `rate_limit_blocked_total{path}` — contador de requisições bloqueadas por rate limiting

- Capacidade do usuário atual via endpoint dedicado:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/auth/capacity -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```
  Retorna os mesmos campos de `capacity` acima, calculados com base em suas licenças ativas e dispositivos.
  O endpoint também inclui o header `X-Capacity-Remaining` com o valor restante atual:
  ```powershell
  (Invoke-WebRequest -Uri http://localhost:8000/auth/capacity -Headers @{ Authorization = "Bearer $token" }).Headers["X-Capacity-Remaining"]
  ```

- Perfil atual (`/auth/me`), usando o token obtido no login:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/auth/me -Headers @{ Authorization = "Bearer $token" }
  ```

- Logout (stateless):
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/auth/logout -Method Post
  ```

- Registro de usuário:
  ```powershell
  $body = '{"username":"novo@example.com","password":"seguro123","full_name":"Novo Usuário"}'
  Invoke-RestMethod -Uri http://localhost:8000/auth/register -Method Post -ContentType 'application/json' -Body $body
  ```
  Após registrar, realize o login normalmente com o novo usuário.

Notas:
- O login prioriza usuários persistentes no banco (`UserAccount`); se não encontrar, faz fallback para `FAKE_USERS` em memória (apenas dev/demo).
- Senhas no banco são armazenadas com hash `bcrypt` via `passlib`; nunca salvamos senhas em texto plano.
- Configure um `SECRET_KEY` via `.env` para tokens mais seguros.

## Dispositivos (SQLModel)

- Banco: SQLite local em `backend/webplay.db` (criado automaticamente no startup).
- Registrar dispositivo do usuário atual:
  ```powershell
  $token = (Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}').access_token
  $body = '{"fingerprint":"device-abc-123","name":"Meu PC","platform":"Windows 11"}'
  Invoke-RestMethod -Uri http://localhost:8000/devices/register -Method Post -ContentType 'application/json' -Body $body -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```
  O registro responde também com o header `X-Capacity-Remaining` indicando quanto ainda pode registrar.
  Para ler headers, utilize `Invoke-WebRequest`:
  ```powershell
  $resp = Invoke-WebRequest -Uri http://localhost:8000/devices/register -Method Post -ContentType 'application/json' -Body $body -Headers @{ Authorization = "Bearer $token" }
  $resp.Headers["X-Capacity-Remaining"]
  ```

- Listar seus dispositivos:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/devices/me -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```

- Remover um dispositivo seu:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/devices/1 -Method Delete -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```

Notas:
- O registro é idempotente por `fingerprint` + usuário: se já existir, retorna o mesmo registro.
- Modelos básicos em `app/models.py` (User, Device, License) — em breve conectaremos com usuários persistentes.
- Limite opcional por licença: defina `DEVICES_PER_LICENSE` (ex.: `2`). Quando configurado, é necessário ter ao menos uma licença ativa e o número de dispositivos permitidos será `licenças_ativas * DEVICES_PER_LICENSE`.

- Capacidade atual de dispositivos (limites e uso):
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/devices/capacity -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```
  Campos: `active_licenses`, `devices_per_license`, `limit_enabled`, `devices_allowed`, `devices_count`, `devices_remaining`.
  O endpoint também inclui o header `X-Capacity-Remaining` com o valor restante atual:
  ```powershell
  (Invoke-WebRequest -Uri http://localhost:8000/devices/capacity -Headers @{ Authorization = "Bearer $token" }).Headers["X-Capacity-Remaining"]
  ```

## Licenças (SQLModel)

- Criar licença para o usuário atual:
  ```powershell
  $token = (Invoke-RestMethod -Uri http://localhost:8000/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}').access_token
  Invoke-RestMethod -Uri http://localhost:8000/licenses/create -Method Post -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```

- Listar suas licenças:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/licenses/me -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```

- Desativar uma licença:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/licenses/1/deactivate -Method Post -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```

- Definir/alterar plano da licença (usa `LICENSE_PLAN_DEVICE_LIMITS` quando configurado):
  ```powershell
  $body = '{"plan":"silver"}'
  Invoke-RestMethod -Uri http://localhost:8000/licenses/1/set_plan -Method Post -ContentType 'application/json' -Headers @{ Authorization = "Bearer $token" } -Body $body | ConvertTo-Json
  ```
  - Para remover o plano e voltar ao padrão de `DEVICES_PER_LICENSE`, envie `{"plan":null}` ou `{ "plan": "" }`.

- Listar planos disponíveis:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/licenses/plans -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```

Notas:
- Licenças são associadas ao usuário autenticado (`owner_username`). O status inicial é `active` e pode ser alterado para `inactive`.
- É possível limitar dispositivos por licença definindo `DEVICES_PER_LICENSE` no ambiente.
  - Opcionalmente, defina limites por plano no arquivo `app/config.py` via `LICENSE_PLAN_DEVICE_LIMITS` (ex.: `{"bronze":1,"silver":2,"gold":5}`). Quando `DEVICES_PER_LICENSE > 0`, cada licença ativa somará o limite do seu plano se definido; caso contrário, usa o valor padrão de `DEVICES_PER_LICENSE`.

- Regras da licença do usuário:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/licenses/rules -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```
  Retorna: `active_licenses`, `devices_per_license`, `devices_allowed`, `devices_count`, `limit_enabled`, `limit_reached`.
  O endpoint também inclui o header `X-Capacity-Remaining` com o valor restante atual:
  ```powershell
  (Invoke-WebRequest -Uri http://localhost:8000/licenses/rules -Headers @{ Authorization = "Bearer $token" }).Headers["X-Capacity-Remaining"]
  ```

- UI simples para visualizar capacidade e licenças:
  - Página: `GET /ui/capacity`
  - Possui formulário de login (usuário/senha) e exibe:
    - Resumo `/licenses/summary` (inclui `X-Capacity-Remaining`)
    - Capacidade `/auth/capacity`
    - Avisos quando `devices_remaining_total` está em 0 ou ≤ 1
  - Para testar localmente (servidor em execução):
    - Abra `http://localhost:8000/ui/capacity` no browser
    - Use `admin@example.com` / `admin123` e explore os dados

## UI de Diagnóstico (sem dependências externas)

- Páginas HTML servidas pelo backend em `/ui/*` para uso rápido sem Node.js ou cadastro externo:
  - `GET /ui/catalog` — catálogo enriquecido com EPG; filtro por nome/grupo e link para stream.
  - `GET /ui/devices` — login, listagem de dispositivos do usuário e registro de novos.
  - `GET /ui/audit` — login e listagem dos eventos de auditoria (`auth.login`, `auth.refresh`, `auth.revoke`, `auth.register`).

- Como acessar localmente (servidor iniciado):
  - `http://localhost:8000/ui/catalog`
  - `http://localhost:8000/ui/devices`
  - `http://localhost:8000/ui/audit`

- Observações:
  - Envie usuário/senha no formulário das páginas para autenticar.
  - As respostas incluem `X-Request-ID` para correlação com logs e auditoria.
  - Usuário demo disponível em dev: `admin@example.com` / `admin123`.

- Resumo de licenças (agregado):
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/licenses/summary -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```
  Retorna: `active_licenses`, `inactive_licenses`, `by_plan_active` (dict), `devices_per_license`, `devices_allowed_total`, `devices_count`, `devices_remaining_total`, `limit_enabled`.
  O endpoint também inclui o header `X-Capacity-Remaining` com o valor de `devices_remaining_total`:
  ```powershell
  (Invoke-WebRequest -Uri http://localhost:8000/licenses/summary -Headers @{ Authorization = "Bearer $token" }).Headers["X-Capacity-Remaining"]
  ```

## Observabilidade e Métricas

- Endpoint Prometheus:
  - `GET http://localhost:8000/metrics` (formato `text/plain; version=0.0.4`)
- Middleware coleta automaticamente:
  - `http_requests_total{method, path, status}`
  - `http_request_duration_seconds{method, path, status}` com buckets padrões
- Métricas de capacidade:
  - `user_capacity_remaining{username, context}` — gauge com a capacidade restante por usuário e contexto (`auth_login`, `auth_capacity`, `devices_register`, `devices_capacity`, `licenses_rules`, `licenses_summary`).
  - `capacity_limit_reached_total{context}` — contador incrementado quando o registro de dispositivo encontra limite (`devices_register`).
- `X-Request-ID`:
  - Header incluído em todas as respostas; pode ser enviado no request para propagar o mesmo ID.

Como testar (PowerShell):
```powershell
Invoke-RestMethod -Uri http://localhost:8000/health -Headers @{ 'X-Request-ID' = 'test-123' } -Method Get | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/metrics -Method Get | Select-Object -First 40
 # Verificar métricas de capacidade
 Invoke-RestMethod -Uri http://localhost:8000/auth/capacity -Headers @{ Authorization = "Bearer $token" } | Out-Null
 (Invoke-RestMethod -Uri http://localhost:8000/metrics).Split("`n") | Where-Object { $_ -match 'user_capacity_remaining' }
```

## Auditoria

- Registrar ações de usuário: criação/desativação de licenças, definição de plano, registro e remoção de dispositivo.

- Listar seus logs de auditoria:
  ```powershell
  Invoke-RestMethod -Uri http://localhost:8000/audit/me -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```
  Parâmetros:
  - `limit` (opcional, padrão 50, máximo 200)
  - `offset` (opcional, padrão 0)
  - `actions` (opcional, repetível) — ex.: `?actions=license.create&actions=device.register`
  - `resources` (opcional, repetível) — ex.: `?resources=license&resources=device`
  - `from_time`, `to_time` (opcional, ISO8601; assume UTC se sem timezone)

  Exemplo com filtros e paginação:
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:8000/audit/me?actions=license.create&resources=license&limit=20&offset=0" -Headers @{ Authorization = "Bearer $token" } | ConvertTo-Json
  ```

## Catálogo EPG (XMLTV)

- Variável de ambiente: `EPG_SOURCE`
  - Aceita caminho relativo no diretório `backend` (ex.: `sample.xml`) ou URL (ex.: `https://.../epg.xml`)
  - Padrão: `sample.xml` (arquivo de exemplo incluso)
- Endpoints:
  - `GET /catalog/epg` — retorna canais e a grade completa normalizada
    - Query opcionais (globais):
      - `start`, `end` (ambos ISO8601). Se o timezone for omitido, assume UTC.
      - `limit_per_channel` (inteiro ≥ 1) e `offset_per_channel` (inteiro ≥ 0) para paginação por canal.
    - O filtro retorna programas que tenham sobreposição com o intervalo informado. Em seguida, é aplicada a paginação por canal (`offset_per_channel` primeiro, depois `limit_per_channel`).
  - `GET /catalog/epg/{channel_id}` — retorna dados do canal e sua programação
    - Query opcionais:
      - `start`, `end` (ambos ISO8601). Se o timezone for omitido, assume UTC.
      - `limit` (inteiro ≥ 1) e `offset` (inteiro ≥ 0) para paginação dos resultados
    - O filtro retorna programas que tenham sobreposição com o intervalo informado. Se apenas `start` for informado, retorna do instante em diante. Se apenas `end` for informado, retorna até o instante. Em seguida, é aplicada a paginação (`offset` primeiro, depois `limit`).
- Cache: o XMLTV é armazenado em cache para reduzir I/O e latência
  - TTL configurável via `EPG_TTL_SECONDS` (padrão: `300` segundos)

Como testar (PowerShell):
```powershell
# EPG local (padrão usa backend/sample.xml)
Invoke-RestMethod -Uri http://localhost:8000/catalog/epg -Method Get | ConvertTo-Json -Depth 4 | Out-Host
Invoke-RestMethod -Uri http://localhost:8000/catalog/epg/jctv -Method Get | ConvertTo-Json -Depth 4 | Out-Host

# Filtro temporal global + paginação por canal
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg?start=2025-01-01T08:00:00Z&end=2025-01-01T09:00:00Z&limit_per_channel=1&offset_per_channel=0" -Method Get | ConvertTo-Json -Depth 6 | Out-Host
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg?start=2025-01-01T08:00:00Z&end=2025-01-01T09:00:00Z&limit_per_channel=1&offset_per_channel=1" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

# Filtro temporal por canal (intervalo)
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg/jctv?start=2025-01-01T08:30:00Z&end=2025-01-01T10:00:00Z" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

# Apenas a partir de um instante
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg/jctv?start=2025-01-01T09:00:00Z" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

# Apenas até um instante
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg/jctv?end=2025-01-01T08:59:00Z" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

# Paginação: retornar apenas 1 item por vez
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg/jctv?start=2025-01-01T08:00:00Z&end=2025-01-01T11:00:00Z&limit=1&offset=0" -Method Get | ConvertTo-Json -Depth 6 | Out-Host
Invoke-RestMethod -Uri "http://localhost:8000/catalog/epg/jctv?start=2025-01-01T08:00:00Z&end=2025-01-01T11:00:00Z&limit=1&offset=1" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

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
    - Query opcionais: `include_now=true|false`, `time` (ISO8601; assume UTC se omitido)
    - Quando `include_now=true`, o payload inclui `current` e `next` por canal, calculados com base no EPG e no instante informado (ou no horário atual se `time` não for fornecido).
  - `GET /catalog/now` — para cada canal, programa atual e próximo (se houver)
    - Query opcional: `time` (ISO8601). Se o timezone for omitido, assume UTC.
  - `GET /catalog/next` — para cada canal, apenas o próximo programa (se houver)
    - Query opcional: `time` (ISO8601). Se o timezone for omitido, assume UTC.

- Cache do M3U:
  - TTL configurável via `M3U_TTL_SECONDS` (padrão: `300` segundos)
  - Para forçar recarregamento, utilize `force=true` em `GET /catalog/m3u` ou `GET /catalog/channels`

Exemplos (PowerShell):
```powershell
# Forçar atualização do M3U ignorando cache
Invoke-RestMethod -Uri "http://localhost:8000/catalog/m3u?force=true" -Method Get | Select-Object -First 5
Invoke-RestMethod -Uri "http://localhost:8000/catalog/channels?force=true" -Method Get | ConvertTo-Json -Depth 3 | Out-Host

# Ajustar TTLs via ambiente (.env ou variável de sessão)
$env:EPG_TTL_SECONDS = '120'
$env:M3U_TTL_SECONDS = '60'
```

Observações:
- A associação M3U ↔ EPG é feita por `tvg-id` (M3U) e `channel.id` (XMLTV) com comparação case-insensitive (por exemplo, `JCTV` ↔ `jctv`).
- Fallback: quando `tvg-id` estiver ausente ou não casar, usamos o nome do canal (`name`) normalizado (lowercase/trim) para tentar encontrar o EPG correspondente.
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

# Canais enriquecidos incluindo current/next (útil para reduzir round-trips)
Invoke-RestMethod -Uri "http://localhost:8000/catalog/channels/enriched?include_now=true&time=2025-01-01T08:30:00Z" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

# Somente o próximo programa por canal
Invoke-RestMethod -Uri "http://localhost:8000/catalog/next?time=2025-01-01T08:30:00Z" -Method Get | ConvertTo-Json -Depth 6 | Out-Host

## Docker

Build e run do backend:
```powershell
cd backend
docker build -t webplay-backend .
docker run -p 8000:8000 --env SECRET_KEY="dev" --env M3U_SOURCE=sample.m3u --env EPG_SOURCE=sample.xml webplay-backend
```

## Deploy no Render.com

- Arquivo `render.yaml` na raiz já define o serviço web com `healthCheckPath: /health` e variáveis de ambiente.
- Instruções resumidas:
  - Conecte o repositório ao Render
  - Escolha plano gratuito para testes
  - `buildCommand`: `pip install -r backend/requirements.txt`
  - `startCommand`: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Defina `SECRET_KEY` e ajuste fontes `M3U_SOURCE`/`EPG_SOURCE` conforme o ambiente
```
# Backend WebPlay BTV

## Stripe (Billing)

Este backend possui rotas opcionais para cobrança via Stripe:

- `POST /billing/checkout` — cria uma sessão de checkout (modo assinatura). Requer autenticação e os campos:
  - `price_id`: ID do preço no Stripe (ex.: `price_...`).
  - `success_url`: URL de sucesso para redirecionamento.
  - `cancel_url`: URL de cancelamento.

- `POST /billing/webhook` — endpoint para webhooks do Stripe. Processa o evento `checkout.session.completed` e cria/atualiza uma licença ativa para o usuário definido em `client_reference_id`.
  - Suporta também `customer.subscription.updated` (atualiza `status` e `plan`) e `customer.subscription.deleted` (inativa a licença vinculada via `external_id`).

- `POST /billing/portal` — cria uma sessão do Billing Portal para o usuário autenticado.
  - Body: `{ "return_url": "https://example.com/account" }`
  - Pré-requisito: o usuário deve ter `stripe_customer_id` salvo (preenchido no webhook de checkout).
  - Resposta: `{ "url": "https://billing.stripe.com/session/..." }`

- `GET /billing/subscription/me` — lista as assinaturas do Stripe do usuário autenticado.
  - Pré-requisito: `stripe_customer_id` associado ao usuário.
  - Resposta: lista de objetos `{ id, status, plan }`.

### Configuração

Defina as variáveis de ambiente:

- `STRIPE_SECRET_KEY` — chave secreta de API do Stripe.
- `STRIPE_WEBHOOK_SECRET` — segredo do endpoint de webhook no Stripe.

Campos adicionais:
- `UserAccount.stripe_customer_id` — ID do cliente no Stripe, usado para gerar sessão do Billing Portal.
- `License.external_id` — ID externo da assinatura (ex.: `subscription.id`), usado para correlacionar e atualizar status/plano.

Opcionalmente, ajuste `DEVICES_PER_LICENSE` e `LICENSE_PLAN_DEVICE_LIMITS` em `app/config.py` para controlar limites por plano. O campo `plan` da licença é preenchido com o `price.id` (ou `nickname/product`) retornado pela assinatura.

Observações:

- Para associar a assinatura ao usuário, o checkout usa `client_reference_id` com `username` atual.
- O webhook atual foca em `checkout.session.completed`. Suporte a `subscription.updated/deleted` pode ser adicionado conforme a necessidade (ex.: para pausar/cancelar assinaturas).
- Em produção, configure o webhook do Stripe para apontar para `/billing/webhook` e use o segredo correto.
usuario: admin@example.com
senha: admin123
