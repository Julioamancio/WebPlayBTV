from fastapi import APIRouter, Response


router = APIRouter(prefix="/ui", tags=["ui"])


@router.get("/capacity")
def ui_capacity():
    html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Resumo de Capacidade</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; }
    .box { border: 1px solid #ccc; padding: 1rem; margin-top: 1rem; border-radius: 6px; }
    label { display:block; margin: 0.5rem 0 0.25rem; }
    input { width: 320px; padding: 0.5rem; }
    button { padding: 0.6rem 1rem; margin-top: 1rem; }
    pre { background: #f7f7f7; padding: 0.75rem; overflow-x: auto; }
    .warning { color: #b80; font-weight: bold; }
    .error { color: #b00; font-weight: bold; }
  </style>
</head>
<body>
  <h1>Resumo de Capacidade</h1>

  <div class="box">
    <h2>Login</h2>
    <label for="username">Usuário</label>
    <input id="username" type="email" placeholder="admin@example.com" value="admin@example.com" />
    <label for="password">Senha</label>
    <input id="password" type="password" placeholder="admin123" value="admin123" />
    <button id="loginBtn">Entrar</button>
    <div id="loginStatus"></div>
  </div>

  <div class="box">
    <h2>Capacidade e Licenças</h2>
    <p>Header <code>X-Capacity-Remaining</code>: <span id="headerCapacity">-</span></p>
    <div id="warning" class="warning"></div>
    <h3>/licenses/summary</h3>
    <pre id="summaryJson">{}</pre>
    <h3>/auth/capacity</h3>
    <pre id="capacityJson">{}</pre>
  </div>

  <script>
    let token = null;
    const qs = (id) => document.getElementById(id);

    async function login() {
      const username = qs('username').value;
      const password = qs('password').value;
      qs('loginStatus').textContent = 'Autenticando...';
      try {
        const resp = await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        if (!resp.ok) {
          throw new Error('Falha no login: ' + resp.status);
        }
        const data = await resp.json();
        token = data.access_token;
        qs('loginStatus').textContent = 'Logado';
        await loadSummary();
        await loadCapacity();
      } catch (err) {
        console.error(err);
        qs('loginStatus').innerHTML = '<span class="error">' + err.message + '</span>';
      }
    }

    async function loadSummary() {
      if (!token) return;
      const resp = await fetch('/licenses/summary', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const text = await resp.text();
      try {
        const json = JSON.parse(text);
        qs('summaryJson').textContent = JSON.stringify(json, null, 2);
        const headerCap = resp.headers.get('X-Capacity-Remaining');
        if (headerCap) qs('headerCapacity').textContent = headerCap;
        // warning
        if (json.devices_remaining_total === 0) {
          qs('warning').textContent = 'Capacidade esgotada: ative/crie licenças para registrar novos dispositivos.';
        } else if (json.devices_remaining_total <= 1) {
          qs('warning').textContent = 'Capacidade quase no fim: considere revisar suas licenças.';
        } else {
          qs('warning').textContent = '';
        }
      } catch (e) {
        qs('summaryJson').textContent = text;
      }
    }

    async function loadCapacity() {
      if (!token) return;
      const resp = await fetch('/auth/capacity', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const text = await resp.text();
      try {
        const json = JSON.parse(text);
        qs('capacityJson').textContent = JSON.stringify(json, null, 2);
      } catch (e) {
        qs('capacityJson').textContent = text;
      }
    }

    qs('loginBtn').addEventListener('click', login);
  </script>
</body>
</html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")

