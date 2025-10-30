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
  <title>Capacidade - WEB Player JCTV</title>
  <style>
    :root { --bg1:#0b0d18; --bg2:#260b17; --tile:#821a1a; --tile-hover:#9c1f1f; --text:#e7e7e7; --muted:#bdbdbd; }
    html, body { height: 100%; margin:0; }
    body { color: var(--text); font-family: "Segoe UI", Roboto, Arial, sans-serif; background: radial-gradient(1200px 600px at 20% 15%, var(--bg2), var(--bg1)); font-size: 18px; }
    .navbar { display:grid; grid-template-columns: 300px 1fr 300px; align-items:center; padding:20px 30px; background: linear-gradient(0deg, rgba(20,20,26,0.40), rgba(20,20,26,0.55)); border-bottom:1px solid rgba(255,255,255,0.08); }
    .brand { display:flex; align-items:center; gap:15px; font-size: 20px; }
    .brand .logo { width:48px; height:48px; background:var(--tile); border-radius:6px; display:grid; place-items:center; color:#fff; }
    .brand .logo svg { width:32px; height:32px; fill:#fff; }
    .tabs { display:flex; gap:30px; align-items:center; }
    .tab { color: var(--muted); font-weight: 600; text-decoration:none; padding:12px 0; font-size: 18px; }
    .tab.active { color:#fff; border-bottom:3px solid var(--tile); }
    .nav-actions { display:flex; justify-content:flex-end; }
    .btn { padding: 14px 22px; background: var(--tile); color:#fff; border:none; border-radius:10px; cursor:pointer; font-weight:600; text-decoration:none; font-size: 18px; }
    .btn:hover { background: var(--tile-hover); }
    .container { max-width: 1200px; margin: 0 auto; padding: 30px; }
    .card { background: rgba(20,20,26,0.65); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 28px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: all 0.2s ease; margin-bottom: 24px; }
    .card:hover { border-color: rgba(255,255,255,0.15); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
    h1 { font-size: 36px; margin: 0 0 20px; font-weight: 700; }
    h2 { font-size: 28px; margin: 0 0 16px; font-weight: 600; }
    p { margin: 0 0 16px; color: var(--muted); font-size: 18px; }
    label { display:block; font-size: 20px; margin: 16px 0 10px; color: var(--muted); font-weight: 500; }
    input { width: 100%; max-width: 450px; padding: 16px 20px; border-radius: 12px; border: 2px solid rgba(255,255,255,0.15); background: rgba(14,14,18,0.8); color:#fff; box-sizing: border-box; font-size: 18px; }
    button { padding: 16px 28px; background: var(--tile); color:#fff; border:none; border-radius:10px; cursor:pointer; font-weight:600; font-size: 18px; }
    button:hover { background: var(--tile-hover); }
    pre { background: rgba(14,14,18,0.8); border: 1px solid rgba(255,255,255,0.10); color:#ddd; padding: 16px; border-radius: 12px; font-size: 16px; }
    .row { display:flex; gap: 24px; flex-wrap: wrap; }
    .col { flex: 1 1 480px; }
    .warning { color: #ffdc8c; font-weight: bold; font-size: 18px; }
    .error { color: #ff8c8c; font-weight: bold; font-size: 18px; }
    code { background: rgba(255,255,255,0.08); padding: 4px 8px; border-radius: 4px; }
    .metrics { display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-top: 12px; }
    .metric { background: rgba(14,14,18,0.8); border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; padding: 14px; }
    .metric .label { color: var(--muted); font-size: 14px; }
    .metric .value { font-size: 22px; font-weight: 700; }
    .progress { height: 10px; background: rgba(255,255,255,0.08); border-radius: 6px; overflow: hidden; margin-top: 10px; }
    .progress .fill { height: 100%; background: linear-gradient(90deg, #4caf50, #81c784); width: 0%; }
    .toolbar-sm { display:flex; gap:10px; align-items:center; margin-top: 10px; }
    .tips { margin-top: 8px; color: var(--muted); font-size: 16px; }
    .tips li { margin-bottom: 6px; }
  </style>
</head>
<body>
  <div class="navbar">
    <div class="brand"><div class="logo" aria-label="Logo robô"><svg viewBox="0 0 24 24" role="img" aria-hidden="true"><rect x="5" y="7" width="14" height="10" rx="3"></rect><circle cx="9" cy="12" r="1.6"></circle><circle cx="15" cy="12" r="1.6"></circle><rect x="11" y="3" width="2" height="3"></rect></svg></div><strong>WEB Player JCTV</strong></div>
    <div class="tabs">
      <a class="tab" href="/ui/catalog">Catálogo</a>
      <a class="tab" href="/ui/devices">Dispositivos</a>
      <a class="tab active" href="/ui/capacity">Capacidade</a>
    </div>
    <div class="nav-actions"><a class="btn" href="/ui/home">← Voltar</a></div>
  </div>
  <div class="container">
    <h1>Resumo de Capacidade</h1>
    <div class="row">
      <div class="col">
        <div class="card">
          <h2>Login</h2>
          <p>Faça login e o token será usado nas chamadas abaixo.</p>
          <label for="username">Usuário</label>
          <input id="username" type="email" placeholder="admin@example.com" value="admin@example.com" />
          <label for="password">Senha</label>
          <input id="password" type="password" placeholder="admin123" value="admin123" />
          <div class="toolbar" style="display:flex; gap:10px; margin-top: 10px;">
            <button id="loginBtn">Entrar</button>
            <div id="loginStatus" class="muted" style="align-self:center;"></div>
          </div>
        </div>
      </div>
      <div class="col">
        <div class="card">
          <h2>Capacidade e Licenças</h2>
          <p>Header <code>X-Capacity-Remaining</code>: <span id="headerCapacity">-</span></p>
          <div class="toolbar-sm">
            <button id="refreshBtn">Atualizar</button>
            <button id="copyHeaderBtn">Copiar header</button>
            <span id="refreshStatus" class="muted"></span>
          </div>
          <div id="warning" class="warning"></div>
          <div class="metrics">
            <div class="metric">
              <div class="label">Licenças ativas</div>
              <div id="mActiveLicenses" class="value">0</div>
            </div>
            <div class="metric">
              <div class="label">Dispositivos por licença</div>
              <div id="mPerLicense" class="value">0</div>
            </div>
            <div class="metric">
              <div class="label">Permitidos</div>
              <div id="mAllowed" class="value">0</div>
              <div class="progress"><div id="progressFill" class="fill"></div></div>
            </div>
            <div class="metric">
              <div class="label">Registrados</div>
              <div id="mCount" class="value">0</div>
            </div>
            <div class="metric">
              <div class="label">Restantes</div>
              <div id="mRemaining" class="value">0</div>
            </div>
            <div class="metric">
              <div class="label">Limite habilitado</div>
              <div id="mLimit" class="value">false</div>
            </div>
          </div>
          <h3 style="margin-top:18px;">/licenses/summary</h3>
          <pre id="summaryJson">{}</pre>
          <h3>/auth/capacity</h3>
          <pre id="capacityJson">{}</pre>
          <ul class="tips">
            <li>Entre com seu usuário e senha para carregar os dados.</li>
            <li>“Permitidos” = licenças ativas × dispositivos por licença.</li>
            <li>“Restantes” = Permitidos − Registrados; também no header <code>X-Capacity-Remaining</code>.</li>
            <li>Use “Atualizar” para reconsultar após mudanças de licenças/dispositivos.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

  <script>
    let token = null;
    const qs = (id) => document.getElementById(id);
    function setText(id, value) { const el = qs(id); if (el) el.textContent = String(value); }
    function renderMetricsFromSummary(json) {
      const active = json.active_licenses ?? 0;
      const per = json.devices_per_license ?? 0;
      const allowed = json.devices_allowed_total ?? 0;
      const count = json.devices_count ?? 0;
      const remaining = json.devices_remaining_total ?? 0;
      const limit = json.limit_enabled ?? false;
      setText('mActiveLicenses', active);
      setText('mPerLicense', per);
      setText('mAllowed', allowed);
      setText('mCount', count);
      setText('mRemaining', remaining);
      setText('mLimit', limit ? 'true' : 'false');
      const fill = qs('progressFill');
      const pct = allowed > 0 ? Math.min(100, Math.round((count / allowed) * 100)) : 0;
      if (fill) fill.style.width = pct + '%';
      if (remaining <= 0 && limit) { qs('warning').textContent = 'Atenção: sua capacidade de dispositivos está esgotada.'; } else { qs('warning').textContent = ''; }
    }

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
        qs('loginStatus').innerHTML = '<span class=\"error\">' + err.message + '</span>';
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
        renderMetricsFromSummary(json);
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
      const header = resp.headers.get('X-Capacity-Remaining');
      if (header) qs('headerCapacity').textContent = header;
    }
    qs('loginBtn').addEventListener('click', login);
    qs('refreshBtn').addEventListener('click', async () => { 
      qs('refreshStatus').textContent = 'Atualizando...'; 
      await loadSummary(); await loadCapacity(); 
      qs('refreshStatus').textContent = 'OK'; 
    });
    qs('copyHeaderBtn').addEventListener('click', async () => {
      const v = qs('headerCapacity').textContent || '';
      try { await navigator.clipboard.writeText(v); qs('refreshStatus').textContent = 'Header copiado'; } catch (e) { qs('refreshStatus').textContent = 'Falha ao copiar'; }
    });
  </script>
</body>
</html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/catalog")
def ui_catalog():
    html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Catálogo de Canais - WEB Player JCTV</title>
  <style>
    :root {
      --bg1: #0b0d18; --bg2: #260b17; --tile: #821a1a; --tile-hover: #9c1f1f; --text: #e7e7e7; --muted: #bdbdbd;
    }
    html, body { height: 100%; margin: 0; }
    body {
      color: var(--text);
      font-family: "Segoe UI", Roboto, Arial, sans-serif;
      background: radial-gradient(1200px 600px at 20% 15%, var(--bg2), var(--bg1));
      min-height: 100vh;
      font-size: 18px;
    }
    /* Navbar com abas e busca */
    .navbar { 
      display: grid; grid-template-columns: 300px 1fr 450px; align-items: center;
      padding: 20px 30px; background: linear-gradient(0deg, rgba(20,20,26,0.40), rgba(20,20,26,0.55));
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .brand { display: flex; align-items: center; gap: 15px; }
    .brand .logo {
      width: 48px; height: 48px; background: var(--tile); border-radius: 6px; 
      display: grid; place-items: center; color: #fff; font-weight: 700; font-size: 20px;
    }
    .brand .logo svg { width: 32px; height: 32px; fill: #fff; }
    .brand strong { font-size: 20px; }
    .tabs { display: flex; gap: 30px; align-items: center; }
    .tab { color: var(--muted); font-weight: 600; cursor: pointer; padding: 12px 0; font-size: 18px; }
    .tab.active { color: #fff; border-bottom: 3px solid var(--tile); }
    .searchbar { display: flex; gap: 15px; justify-content: flex-end; }
    .searchbar input { width: 280px; padding: 16px 20px; border-radius: 25px; border: 2px solid rgba(255,255,255,0.15); background: rgba(14,14,18,0.8); color: #fff; font-size: 18px; }
    .searchbar select { padding: 16px 20px; border-radius: 15px; border: 2px solid rgba(255,255,255,0.15); background: rgba(14,14,18,0.8); color: #fff; font-size: 18px; }
    /* Layout com sidebar */
    .layout { display: grid; grid-template-columns: 350px 1fr; gap: 30px; }
    .sidebar { padding: 28px; border-right: 1px solid rgba(255,255,255,0.08); }
    .sidebar .section { margin-bottom: 24px; }
    .sidebar .item { display:flex; align-items:center; justify-content: space-between; padding: 16px 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.12); color: var(--muted); cursor: pointer; font-size: 18px; }
    .sidebar .item:hover { color: #fff; border-color: rgba(255,255,255,0.18); }
    .sidebar .item .dot { width: 12px; height: 12px; background: var(--tile); border-radius: 50%; }
    .sidebar .item .count { margin-left: 8px; color: var(--muted); font-size: 12px; }
    .subcats { margin: 10px 0 14px 12px; }
    .subitem { padding: 10px 14px; border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; color: var(--muted); cursor: pointer; margin-bottom: 8px; }
    .subitem:hover { border-color: rgba(255,255,255,0.18); color: #ffffff; }
    /* Área de conteúdo */
    .container { padding: 30px; position: relative; }
    .toolbar { display:flex; align-items:center; gap: 20px; margin-top: 16px; margin-bottom: 16px; }
    .toolbar button { padding: 16px 28px; background: var(--tile); color: #fff; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 18px; }
    .toolbar button:hover { background: var(--tile-hover); }
    /* Loader overlay */
    .loader-overlay { position: absolute; inset: 0; display:flex; align-items:center; justify-content:center; background: rgba(0,0,0,0.35); border-radius: 16px; z-index: 10; }
    .loader-overlay.hidden { display:none; }
    .spinner { width: 42px; height: 42px; border: 4px solid rgba(255,255,255,0.25); border-top-color: var(--tile); border-radius: 50%; animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .grid { 
      display: grid; 
      grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); 
      gap: 24px; 
      margin-top: 24px; 
    }
    .card { 
      background: rgba(20,20,26,0.65); 
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px; 
      padding: 24px; 
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      transition: all 0.2s ease;
    }
    .card:hover { 
      border-color: rgba(255,255,255,0.15);
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }
    .channel-header { display: flex; gap: 20px; align-items: center; margin-bottom: 20px; }
    .logo-wrap { width: 72px; height: 72px; display: grid; place-items: center; }
    .channel-logo-img { width: 72px; height: 72px; object-fit: contain; border-radius: 10px; }
    .channel-logo { 
      width: 72px; height: 72px; border-radius: 10px;
      background: rgba(255,255,255,0.05); border: 1px dashed rgba(255,255,255,0.2);
      position: relative; overflow: hidden; display: grid; place-items: center;
    }
    .channel-logo svg { width: 40px; height: 40px; fill: #fff; opacity: 0.92; }
    .hidden { display: none; }
    .skeleton-line { height: 10px; border-radius: 6px; background: rgba(255,255,255,0.08); position: relative; overflow: hidden; }
    .skeleton-button { height: 28px; width: 140px; border-radius: 6px; background: rgba(255,255,255,0.08); position: relative; overflow: hidden; }
    .w-60 { width: 60%; } .w-40 { width: 40%; } .w-80 { width: 80%; } .w-50 { width: 50%; }
    @keyframes shimmer { 0% { transform: translateX(-100%);} 100% { transform: translateX(100%);} }
    .skeleton-line::after, .skeleton-button::after, .card .channel-logo::after { 
      content: ""; position: absolute; inset: 0;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
      animation: shimmer 1.2s infinite;
    }
    @media (prefers-reduced-motion: reduce) {
      .skeleton-line::after, .skeleton-button::after, .card .channel-logo::after { animation: none; }
    }
    .channel-info h3 { margin: 0; font-size: 24px; color: var(--text); font-weight: 600; }
    .channel-info .badges { margin-top: 8px; }
    .badge { 
      display: inline-block; padding: 6px 12px; border-radius: 16px; 
      background: rgba(130,26,26,0.3); color: var(--muted); 
      font-size: 16px; margin-right: 10px; border: 1px solid rgba(130,26,26,0.5);
    }
    .program-info { margin: 20px 0; font-size: 18px; color: var(--muted); }
    .program-info .current { color: var(--text); font-weight: 500; }
    .stream-link { 
      display: inline-block; padding: 12px 24px; background: var(--tile); 
      color: #fff; text-decoration: none; border-radius: 10px; font-size: 18px;
      font-weight: 600; transition: background 0.2s;
    }
    .stream-link:hover { background: var(--tile-hover); }
    .empty-state { 
      text-align: center; padding: 48px 24px; color: var(--muted);
      background: rgba(20,20,26,0.4); border-radius: 12px; margin-top: 24px;
    }
    /* Mini Player + Backdrop */
    .overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.65); z-index: 1000; }
    .mini-player { 
      position: fixed; right: 16px; bottom: 16px; z-index: 1001;
      width: 360px; background: rgba(20,20,26,0.85);
      border: 1px solid rgba(255,255,255,0.15); border-radius: 12px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.6);
      padding: 12px; 
    }
    .mini-player.hidden { display: none; }
    .mini-player .player-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
    .mini-player .close-btn { background: transparent; border: 1px solid rgba(255,255,255,0.25); color: #fff; padding: 6px 10px; border-radius: 8px; cursor: pointer; }
    .mini-player .close-btn:hover { background: rgba(255,255,255,0.08); }
    .mini-player video { width: 100%; height: 200px; background: #000; border-radius: 8px; }
    .mini-player.expanded { inset: 5% 5% auto 5%; right: auto; bottom: auto; width: 90vw; padding: 16px; }
    .mini-player.expanded video { height: 68vh; }
    /* Responsividade catálogo */
    @media (max-width: 1024px) {
      .navbar { grid-template-columns: 180px 1fr; row-gap: 10px; }
      .searchbar { justify-content: flex-start; }
      .searchbar input { width: 100%; max-width: 280px; }
    }
    @media (max-width: 768px) {
      .navbar { grid-template-columns: 1fr; row-gap: 8px; }
      .tabs { overflow-x: auto; white-space: nowrap; }
      .layout { grid-template-columns: 1fr; }
      .sidebar { border-right: none; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; }
      .grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
      .logo-wrap { width: 48px; height: 72px; }
      .channel-logo-img, .channel-logo { width: 48px; height: 72px; border-radius: 6px; }
    }
  </style>
  </head>
  <body>
    <div class="navbar">
      <div class="brand">
        <div class="logo" aria-label="Logo robô">
          <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
            <rect x="5" y="7" width="14" height="10" rx="3"></rect>
            <circle cx="9" cy="12" r="1.6"></circle>
            <circle cx="15" cy="12" r="1.6"></circle>
            <rect x="11" y="3" width="2" height="3"></rect>
          </svg>
        </div>
        <strong>WEB Player JCTV</strong>
      </div>
      <div class="tabs">
        <div id="tabClasses" class="tab">Class</div>
        <div id="tabLive" class="tab active">TV ao vivo</div>
        <div id="tabMovies" class="tab">Filmes</div>
        <div id="tabSeries" class="tab">Séries</div>
      </div>
      <div class="searchbar">
        <input id="searchInput" placeholder="procurar…" />
        <select id="groupFilter">
          <option value="">todos os grupos</option>
        </select>
        <select id="sortSelect">
          <option value="name">ordenar por nome</option>
          <option value="group">ordenar por grupo</option>
          <option value="number">ordenar por número</option>
        </select>
      </div>
    </div>
    <!-- Backdrop + Mini Player -->
    <div id="playerBackdrop" class="overlay hidden"></div>
    <div id="miniPlayer" class="mini-player hidden">
      <div class="player-header">
        <strong id="playerTitle">Player</strong>
        <button class="close-btn" onclick="closePlayer()">Fechar ✕</button>
      </div>
      <video id="catalogVideo" controls playsinline></video>
      <div id="playerStatus" class="muted" style="margin-top:8px;"></div>
    </div>
    <div class="layout">
      <aside class="sidebar">
        <div class="section">
          <div class="item" onclick="location.href='/ui/home'">voltar</div>
          <div class="item">procurar</div>
        </div>
        <div class="section">
          <div class="item">Categorias populares <span class="dot"></span></div>
          <div class="item">Favoritos</div>
          <div class="item">DEMO VOD</div>
        </div>
        <div class="section">
          <div class="item">Pastas e categorias</div>
          <div id="catsList" class="cats-list"></div>
        </div>
      </aside>
      <main class="container">
        <h1 style="margin: 0 0 8px; font-size: 24px;">Catálogo de Canais</h1>
        <p style="margin: 0; color: var(--muted);">Navegue pelos canais disponíveis e acesse transmissões ao vivo.</p>
        <div class="toolbar">
          <button id="reload">Recarregar</button>
        </div>
        <div id="netLoader" class="loader-overlay hidden"><div class="spinner" aria-label="carregando"></div></div>
        <div id="grid" class="grid"></div>
      </main>
    </div>
    <script>
      const grid = document.getElementById('grid');
      const netLoader = document.getElementById('netLoader');
      const searchInput = document.getElementById('searchInput');
      const groupFilter = document.getElementById('groupFilter');
      const sortSelect = document.getElementById('sortSelect');
      const reload = document.getElementById('reload');
      const tabs = {
        classes: document.getElementById('tabClasses'),
        live: document.getElementById('tabLive'),
        movies: document.getElementById('tabMovies'),
        series: document.getElementById('tabSeries'),
      };
      // Define a aba inicial a partir da query string (?tab=live|movies|series|classes)
      const params = new URLSearchParams(location.search);
      const initialTab = (params.get('tab') || 'live').toLowerCase();
      let currentCategory = ['live','movies','series','classes'].includes(initialTab) ? initialTab : 'live';
      // Atualiza estado visual das abas conforme a aba inicial
      Object.values(tabs).forEach(t => t.classList.remove('active'));
      if (tabs[currentCategory]) { tabs[currentCategory].classList.add('active'); }
      let channels = [];

      function showSkeleton(n = 8) {
        grid.innerHTML = Array.from({ length: n }).map(() => `
          <div class=\"card\">
            <div class=\"channel-header\">
              <div class=\"channel-logo\"></div>
              <div class=\"channel-info\">
                <div class=\"skeleton-line w-60\"></div>
                <div class=\"skeleton-line w-40\"></div>
              </div>
            </div>
            <div class=\"program-info\">
              <div class=\"skeleton-line w-80\"></div>
              <div class=\"skeleton-line w-50\"></div>
            </div>
            <div class=\"skeleton-button\"></div>
          </div>
        `).join('');
      }

      function getToken(){ try { return localStorage.getItem('access_token'); } catch { return null; } }
      async function loadChannels(force=false) {
        showSkeleton(8);
        try { netLoader.classList.remove('hidden'); } catch {}
        try {
          const t = getToken();
          const endpoint = t ? '/catalog/channels/enriched/me' : '/catalog/channels/enriched';
          const url = endpoint + (force ? '?force=true' : '');
          const opts = t ? { headers: { 'Authorization': 'Bearer ' + t } } : {};
          const resp = await fetch(url, opts);
          const data = await resp.json();
          channels = Array.isArray(data) ? data : [];
          try {
            const groups = Array.from(new Set(channels.map(c => c.group).filter(Boolean))).sort((a,b) => String(a).localeCompare(String(b)));
            groupFilter.innerHTML = '<option value="">todos os grupos</option>' + groups.map(g => `<option value="${String(g).toLowerCase()}">${String(g)}</option>`).join('');
            buildCatsList();
          } catch(e) { console.warn('falha ao popular grupos', e); }
          render();
        } catch (e) {
          grid.innerHTML = '<div class="empty-state">❌ Erro ao carregar canais: ' + (e?.message || e) + '</div>';
        } finally { try { netLoader.classList.add('hidden'); } catch {} }
      }

      function classifyChannel(c){
        const g = (c.group||'').toLowerCase();
        const n = (c.name||'').toLowerCase();
        if (/(movie|filme|movies|cinema|vod)/.test(g) || /(filme|movie|cinema|vod)/.test(n)) return 'movies';
        if (/(series|serie|seriados|serial)/.test(g) || /(series|serie|epis[oó]dio|temporada)/.test(n)) return 'series';
        return 'live';
      }
      function buildCatsList(){
        const el = document.getElementById('catsList');
        if (!el) return;
        if (!Array.isArray(channels) || channels.length === 0) { el.innerHTML = ''; return; }
        const byCat = { live: [], movies: [], series: [] };
        channels.forEach(c => { const cat = classifyChannel(c); byCat[cat].push(c); });
        const uniqueGroups = arr => Array.from(new Set(arr.map(c => (c.group||'').trim()).filter(Boolean))).sort((a,b) => a.localeCompare(b));
        const liveGroups = uniqueGroups(byCat.live);
        const movieGroups = uniqueGroups(byCat.movies);
        const seriesGroups = uniqueGroups(byCat.series);
        const section = (label, key, groupsArr) => `
          <div class="item sidecat" data-cat="${key}">${label} <span class="count">${byCat[key].length}</span></div>
          <div class="subcats">
            ${groupsArr.map(g => `<div class="subitem" data-cat="${key}" data-group="${g.toLowerCase()}">${g}</div>`).join('')}
          </div>`;
        el.innerHTML = section('Live', 'live', liveGroups) + section('Filmes', 'movies', movieGroups) + section('Séries', 'series', seriesGroups);
        // Clique em categoria principal
        el.querySelectorAll('.sidecat').forEach(node => {
          node.addEventListener('click', ev => {
            const cat = ev.currentTarget.getAttribute('data-cat');
            currentCategory = cat;
            groupFilter.value = '';
            Object.values(tabs).forEach(t => t.classList.remove('active'));
            if (tabs[cat]) tabs[cat].classList.add('active');
            render();
          });
        });
        // Clique em subgrupo
        el.querySelectorAll('.subitem').forEach(node => {
          node.addEventListener('click', ev => {
            const cat = ev.currentTarget.getAttribute('data-cat');
            const grp = ev.currentTarget.getAttribute('data-group');
            currentCategory = cat;
            groupFilter.value = grp;
            Object.values(tabs).forEach(t => t.classList.remove('active'));
            if (tabs[cat]) tabs[cat].classList.add('active');
            render();
          });
        });
      }
      function render() {
        const q = (searchInput?.value || '').toLowerCase();
        const gf = (groupFilter?.value || '').toLowerCase();
        const items = channels.filter(c => {
          const name = (c.name || '').toLowerCase();
          const group = (c.group || '').toLowerCase();
          const matchesQuery = !q || name.includes(q) || group.includes(q);
          if (!matchesQuery) return false;
          if (gf && group !== gf) return false;
          const cat = classifyChannel(c);
          if (currentCategory === 'live') return cat === 'live';
          if (currentCategory === 'movies') return cat === 'movies';
          if (currentCategory === 'series') return cat === 'series';
          return true; // classes
        });
        const key = sortSelect?.value || 'name';
        items.sort((a,b) => {
          if (key === 'group') return (a.group||'').localeCompare(b.group||'');
          if (key === 'number') {
            const pa = parseInt(String(a.tvg_id||'').replace(/\D+/g,'')) || -1;
            const pb = parseInt(String(b.tvg_id||'').replace(/\D+/g,'')) || -1;
            return pa - pb;
          }
          return (a.name||'').localeCompare(b.name||'');
        });
        
        if (items.length === 0) {
          grid.innerHTML = q ? 
            '<div class="empty-state">🔍 Nenhum canal encontrado para "' + q + '"</div>' :
            '<div class="empty-state">📺 Nenhum canal disponível no momento</div>';
          return;
        }
        
        grid.innerHTML = items.map(c => `
          <div class=\"card\">
            <div class=\"channel-header\">
              <div class=\"logo-wrap\">
                ${c.logo ? 
                  `<img class=\"channel-logo-img\" src=\"${c.logo}\" alt=\"Logo ${c.name}\" loading=\"lazy\" onerror=\"this.nextElementSibling && this.nextElementSibling.classList.remove('hidden'); this.remove();\" />` : 
                  ``
                }
                <div class=\"channel-logo ${c.logo ? 'hidden' : ''}\" aria-label=\"Logo padrão\">
                  <svg viewBox=\"0 0 24 24\" role=\"img\" aria-hidden=\"true\">
                    <rect x=\"5\" y=\"7\" width=\"14\" height=\"10\" rx=\"3\"></rect>
                    <circle cx=\"9\" cy=\"12\" r=\"1.6\"></circle>
                    <circle cx=\"15\" cy=\"12\" r=\"1.6\"></circle>
                    <rect x=\"11\" y=\"3\" width=\"2\" height=\"3\"></rect>
                  </svg>
                </div>
              </div>
              <div class=\"channel-info\">
                <h3>${c.name || '(sem nome)'}</h3>
                <div class=\"badges\">
                  ${c.group ? `<span class=\"badge\">${c.group}</span>` : ''}
                  ${c.tvg_id ? `<span class=\"badge\">ID: ${c.tvg_id}</span>` : ''}
                </div>
              </div>
            </div>
            ${c.current || c.next ? `
              <div class=\"program-info\">
                ${c.current ? `<div class=\"current\">🔴 Agora: ${c.current.title || 'Sem informação'}</div>` : ''}
                ${c.next ? `<div>⏭️ Próximo: ${c.next.title || 'Sem informação'}</div>` : ''}
              </div>
            ` : ''}
            <a href=\"#\" onclick=\"openPlayer('${c.url}', '${(c.name||'').replace(/"/g,'\\"')}'); return false;\" class=\"stream-link\">▶️ Assistir</a>
          </div>
        `).join('');
      }

      reload.addEventListener('click', () => loadChannels(true));
      searchInput.addEventListener('input', render);
      groupFilter.addEventListener('change', render);
      sortSelect.addEventListener('change', render);
      Object.values(tabs).forEach(el => el.addEventListener('click', (ev) => {
        Object.values(tabs).forEach(t => t.classList.remove('active'));
        ev.currentTarget.classList.add('active');
        if (ev.currentTarget === tabs.live) currentCategory = 'live';
        else if (ev.currentTarget === tabs.movies) currentCategory = 'movies';
        else if (ev.currentTarget === tabs.series) currentCategory = 'series';
        else currentCategory = 'classes';
        render();
      }));
      loadChannels();
      /* Player logic: supports native, HLS via hls.js, DASH via Shaka */
      const mini = document.getElementById('miniPlayer');
      const backdrop = document.getElementById('playerBackdrop');
      const videoEl = document.getElementById('catalogVideo');
      const playerStatus = document.getElementById('playerStatus');
      const playerTitle = document.getElementById('playerTitle');
      let shakaPlayer = null;

      function isHls(url){ return /\.m3u8($|\?)/i.test(url); }
      function isDash(url){ return /\.mpd($|\?)/i.test(url); }
      function normalizeStreamUrl(url){
        try {
          if (/\.ts(\?|$)/i.test(url)) return url.replace(/\.ts(\?|$)/i, '.m3u8$1');
        } catch {}
        return url;
      }
      function openPlayer(url, title){
        mini.classList.remove('hidden');
        backdrop.classList.add('hidden');
        playerTitle.textContent = title || 'Player';
        playerStatus.textContent = 'Carregando…';
        playUrl(normalizeStreamUrl(url));
      }
      function toggleExpand(force){
        const expand = typeof force === 'boolean' ? force : !mini.classList.contains('expanded');
        if (expand){ mini.classList.add('expanded'); backdrop.classList.remove('hidden'); }
        else { mini.classList.remove('expanded'); backdrop.classList.add('hidden'); }
      }
      function closePlayer(){
        try { if (shakaPlayer) { shakaPlayer.destroy(); shakaPlayer = null; } } catch {}
        try {
          if (videoEl) { videoEl.pause(); videoEl.removeAttribute('src'); videoEl.load(); }
        } catch {}
        mini.classList.add('hidden');
        mini.classList.remove('expanded');
        backdrop.classList.add('hidden');
        playerStatus.textContent = '';
      }
      videoEl.addEventListener('dblclick', () => toggleExpand());
      backdrop.addEventListener('click', () => toggleExpand(false));
      async function playUrl(url){
        // Prefer Shaka for DASH; fallback to HLS.js for HLS; else native
        try {
          if (isDash(url)) {
            if (window.shaka) {
              shakaPlayer = new shaka.Player(videoEl);
              await shakaPlayer.load(url);
              playerStatus.textContent = 'DASH carregado com Shaka';
              return;
            }
          }
          if (isHls(url)) {
            const canNative = videoEl.canPlayType('application/vnd.apple.mpegurl');
            if (canNative) {
              videoEl.src = url; await videoEl.play(); playerStatus.textContent = 'HLS nativo'; return;
            }
            if (window.Hls && Hls.isSupported()) {
              const hls = new Hls(); hls.loadSource(url); hls.attachMedia(videoEl);
              hls.on(Hls.Events.MANIFEST_PARSED, () => { videoEl.play(); playerStatus.textContent = 'HLS via hls.js'; });
              hls.on(Hls.Events.ERROR, (_, data) => { playerStatus.textContent = 'HLS erro: ' + (data?.details || data?.type || ''); });
              return;
            }
          }
          // Fallback: progressive (mp4, webm, etc.)
          videoEl.src = url; await videoEl.play(); playerStatus.textContent = 'Reprodução nativa';
        } catch (e) {
          playerStatus.innerHTML = 'Falha ao reproduzir: ' + (e?.message || e) + ' — <a href="'+url+'" target="_blank" style="color:#fff;">abrir externamente</a>';
        }
      }
    </script>
    <!-- External libs for broad codec/protocol support -->
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script src="https://unpkg.com/shaka-player@latest/dist/shaka-player.compiled.js"></script>
  </body>
</html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/devices")
def ui_devices():
    html = """
<!DOCTYPE html>
<html lang=\"pt-BR\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Dispositivos - WEB Player JCTV</title>
  <style>
    :root { --bg1:#0b0d18; --bg2:#260b17; --tile:#821a1a; --tile-hover:#9c1f1f; --text:#e7e7e7; --muted:#bdbdbd; }
    html, body { height: 100%; margin:0; }
    body { color: var(--text); font-family: \"Segoe UI\", Roboto, Arial, sans-serif; background: radial-gradient(1200px 600px at 20% 15%, var(--bg2), var(--bg1)); font-size: 18px; }
    .navbar { display:grid; grid-template-columns: 300px 1fr 300px; align-items:center; padding:20px 30px; background: linear-gradient(0deg, rgba(20,20,26,0.40), rgba(20,20,26,0.55)); border-bottom:1px solid rgba(255,255,255,0.08); }
    .brand { display:flex; align-items:center; gap:15px; font-size: 20px; }
    .brand .logo { width:48px; height:48px; background:var(--tile); border-radius:6px; display:grid; place-items:center; color:#fff; }
    .brand .logo svg { width:32px; height:32px; fill:#fff; }
    .tabs { display:flex; gap:30px; align-items:center; }
    .tab { color: var(--muted); font-weight: 600; text-decoration:none; padding:12px 0; font-size: 18px; }
    .tab.active { color:#fff; border-bottom:3px solid var(--tile); }
    .container { max-width: 1200px; margin: 0 auto; padding: 30px; }
    .card { background: rgba(20,20,26,0.65); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 28px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: all 0.2s ease; margin-bottom: 24px; }
    .card:hover { border-color: rgba(255,255,255,0.15); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
    h1 { font-size: 36px; margin: 0 0 20px; font-weight: 700; }
    h2 { font-size: 28px; margin: 0 0 16px; font-weight: 600; }
    p { margin: 0 0 16px; color: var(--muted); font-size: 18px; }
    label { display:block; font-size: 20px; margin: 16px 0 10px; color: var(--muted); font-weight: 500; }
    input { width: 100%; max-width: 400px; padding: 16px 20px; border-radius: 12px; border: 2px solid rgba(255,255,255,0.15); background: rgba(14,14,18,0.8); color:#fff; box-sizing: border-box; font-size: 18px; }
    button { padding: 16px 28px; background: var(--tile); color:#fff; border:none; border-radius:10px; cursor:pointer; font-weight:600; font-size: 18px; }
    button:hover { background: var(--tile-hover); }
    ul { padding-left: 2rem; margin: 12px 0 0; font-size: 18px; }
    li { margin-bottom: 8px; }
    .muted { color: var(--muted); font-size: 18px; }
    .error { color: #ffb3b3; font-weight: bold; font-size: 18px; }
    .row { display:flex; gap: 24px; flex-wrap: wrap; }
    .col { flex: 1 1 400px; }
    .nav-actions { display:flex; justify-content:flex-end; }
    .btn { padding: 16px 28px; background: var(--tile); color:#fff; border:none; border-radius:10px; cursor:pointer; font-weight:600; text-decoration:none; font-size: 18px; }
    .btn:hover { background: var(--tile-hover); }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left; }
    .actions { display:flex; gap:8px; }
    /* Cards de playlist */
    .pl-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 16px; }
    .pl-card { background: rgba(14,14,18,0.8); border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; padding: 16px; }
    .pl-head { display:flex; justify-content: space-between; align-items:center; margin-bottom: 8px; }
    .pl-name { font-weight: 700; font-size: 18px; }
    .pl-badge { padding: 6px 10px; border-radius: 8px; background: rgba(255,255,255,0.12); font-size: 14px; }
    .pl-body { color: var(--muted); font-size: 16px; }
    .pl-card a { color: var(--text); text-decoration: none; }
    .pl-card a:hover { text-decoration: underline; }
    .pl-body div { overflow-wrap: anywhere; }
    .pl-actions { display:flex; gap:10px; margin-top: 10px; }
    .pl-loading { margin-top:8px; color: var(--muted); }
    .pl-summary { margin-top:6px; font-size: 16px; }
    .pl-editor { margin-top: 10px; background: rgba(20,20,26,0.5); border: 1px solid rgba(255,255,255,0.08); padding: 12px; border-radius: 8px; }
    .pl-editor label { display:block; font-size: 16px; margin: 10px 0 6px; color: var(--muted); }
    .pl-editor input { width: 100%; padding: 12px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.15); background: rgba(14,14,18,0.8); color:#fff; box-sizing: border-box; }
  </style>
  <script>
    let token = null;
    let lastPlaylists = [];
    const qs = id => document.getElementById(id);
    async function login() {
      qs('loginStatus').textContent = 'Autenticando...';
      try {
        const resp = await fetch('/auth/login', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: qs('username').value, password: qs('password').value })
        });
        if (!resp.ok) throw new Error('Falha no login: ' + resp.status);
        const data = await resp.json();
        token = data.access_token;
        try { localStorage.setItem('access_token', token); } catch {}
        qs('loginStatus').textContent = 'Logado';
        // Após login, carregar dispositivos e listas salvas
        await listDevices();
        await listPlaylists();
      } catch (e) {
        qs('loginStatus').innerHTML = '<span class=\"error\">' + (e?.message || e) + '</span>';
      }
    }
    async function listDevices() {
      if (!token) return;
      const resp = await fetch('/devices/me', { headers: { 'Authorization': 'Bearer ' + token } });
      const data = await resp.json();
      qs('list').innerHTML = Array.isArray(data) && data.length
        ? data.map(d => `<li>${d.name || '(sem nome)'} — ${d.fingerprint} (${d.platform || '-'})</li>`).join('')
        : '<li>Nenhum dispositivo</li>';
    }
    async function registerDevice() {
      if (!token) return;
      qs('registerStatus').textContent = 'Registrando...';
      try {
        const payload = { fingerprint: qs('fp').value, name: qs('name').value, platform: qs('platform').value };
        const resp = await fetch('/devices/register', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }, body: JSON.stringify(payload) });
        if (!resp.ok) throw new Error('Falha ao registrar: ' + resp.status);
        qs('registerStatus').textContent = 'OK';
        await listDevices();
      } catch (e) {
        qs('registerStatus').innerHTML = '<span class=\"error\">' + (e?.message || e) + '</span>';
      }
    }
    async function listPlaylists() {
      if (!token) return;
      try {
        const resp = await fetch('/playlists/me', { headers: { 'Authorization': 'Bearer ' + token } });
        const items = await resp.json();
        lastPlaylists = Array.isArray(items) ? items : [];
        qs('pl_list').innerHTML = lastPlaylists.length ? `
          <div class="pl-grid">
            ${lastPlaylists.map(p => `
              <div class="pl-card" id="pl_card_${p.id}">
                <div class="pl-head">
                  <div class="pl-name">${p.name}</div>
                  <div class="pl-badge">${p.active ? 'Ativa' : 'Inativa'}</div>
                </div>
                <div class="pl-body">
                  <div>Tipo: <code>${p.type}</code></div>
                  <div>Lista: <a href="${p.url}" target="_blank">${p.url}</a></div>
                  <div>EPG: ${p.epg_url ? `<a href="${p.epg_url}" target="_blank">${p.epg_url}</a>` : '-'}</div>
                </div>
                <div class="pl-actions">
                  <button onclick="activatePlaylist(${p.id})">Ativar</button>
                  <button onclick="editPlaylist(${p.id})">Editar</button>
                  <button onclick="deletePlaylist(${p.id})">Excluir</button>
                  <button onclick="reloadPlaylist(${p.id})">Carregar</button>
                </div>
                <div class="pl-loading" id="pl_loading_${p.id}"></div>
                <div class="pl-summary" id="pl_summary_${p.id}"></div>
              </div>
            `).join('')}
          </div>
        ` : '<span class="muted">Nenhuma lista cadastrada</span>';
      } catch (e) {
        qs('pl_status').innerHTML = '<span class=\"error\">' + (e?.message || e) + '</span>';
      }
    }
    async function createPlaylist() {
      if (!token) return;
      qs('pl_status').textContent = 'Salvando...';
      try {
        const name = qs('pl_name').value.trim();
        const type = (qs('pl_type').value || 'm3u').trim();
        const url = qs('pl_url').value.trim();
        const epg_url = qs('pl_epg').value.trim();
        if (!name || !url) {
          qs('pl_status').innerHTML = '<span class=\"error\">Informe pelo menos Nome e URL da lista</span>';
          return;
        }
        const payload = { name, type, url, epg_url };
        const resp = await fetch('/playlists/create', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }, body: JSON.stringify(payload) });
        if (!resp.ok) throw new Error('Falha ao salvar: ' + resp.status);
        const created = await resp.json();
        qs('pl_status').textContent = 'Lista salva. Carregando canais...';
        await listPlaylists();
        await reloadPlaylist(created.id);
      } catch (e) {
        qs('pl_status').innerHTML = '<span class=\"error\">' + (e?.message || e) + '</span>';
      }
    }
    async function editPlaylist(id) {
      if (!token) return;
      const p = lastPlaylists.find(x => x.id === id);
      const card = qs('pl_card_' + id);
      if (!card || !p) return;
      const existing = qs('pl_editor_' + id);
      if (existing) { existing.remove(); return; }
      const esc = (s) => String(s || '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
      const editor = document.createElement('div');
      editor.className = 'pl-editor';
      editor.id = 'pl_editor_' + id;
      editor.innerHTML = `
        <label>Nome</label>
        <input id="pl_edit_name_${id}" value="${esc(p.name)}" />
        <label>URL da lista</label>
        <input id="pl_edit_url_${id}" value="${esc(p.url)}" />
        <label>URL do EPG (opcional)</label>
        <input id="pl_edit_epg_${id}" value="${esc(p.epg_url || '')}" />
        <div class="pl-actions">
          <button onclick="applyEditPlaylist(${id})">Salvar</button>
          <button onclick="cancelEditPlaylist(${id})">Cancelar</button>
        </div>
        <div id="pl_edit_status_${id}" class="muted"></div>
      `;
      card.appendChild(editor);
    }
    async function applyEditPlaylist(id) {
      if (!token) return;
      const name = qs('pl_edit_name_' + id).value.trim();
      const url = qs('pl_edit_url_' + id).value.trim();
      const epg = qs('pl_edit_epg_' + id).value.trim();
      const statusEl = qs('pl_edit_status_' + id);
      try {
        const resp = await fetch(`/playlists/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }, body: JSON.stringify({ name, url, epg_url: epg }) });
        if (!resp.ok) throw new Error('Falha ao editar: ' + resp.status);
        statusEl.textContent = 'Salvo';
        await listPlaylists();
      } catch (e) {
        statusEl.innerHTML = '<span class=\"error\">' + (e?.message || e) + '</span>';
      }
    }
    function cancelEditPlaylist(id) { const el = qs('pl_editor_' + id); if (el) el.remove(); }
    async function deletePlaylist(id) {
      if (!token) return;
      if (!confirm('Excluir esta lista?')) return;
      try {
        const resp = await fetch(`/playlists/${id}`, { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
        if (!resp.ok) throw new Error('Falha ao excluir: ' + resp.status);
        await listPlaylists();
      } catch (e) {
        qs('pl_status').innerHTML = '<span class=\"error\">' + (e?.message || e) + '</span>';
      }
    }
    async function activatePlaylist(id) {
      if (!token) return;
      try {
        const resp = await fetch(`/playlists/${id}/activate`, { method: 'POST', headers: { 'Authorization': 'Bearer ' + token } });
        if (!resp.ok) throw new Error('Falha ao ativar: ' + resp.status);
        await listPlaylists();
      } catch (e) {
        qs('pl_status').innerHTML = '<span class=\"error\">' + (e?.message || e) + '</span>';
      }
    }

    async function reloadPlaylist(id) {
      if (!token) return;
      const loadingEl = qs(`pl_loading_${id}`);
      const summaryEl = qs(`pl_summary_${id}`);
      if (loadingEl) loadingEl.textContent = 'Carregando lista...';
      if (summaryEl) summaryEl.textContent = '';
      try {
        const resp = await fetch(`/playlists/${id}/reload`, { method: 'POST', headers: { 'Authorization': 'Bearer ' + token } });
        if (!resp.ok) throw new Error('Falha ao carregar: ' + resp.status);
        const data = await resp.json();
        if (loadingEl) loadingEl.textContent = `Carregado: ${data.total_channels} canais`;
        const cats = data.categories || {};
        const tv = cats.tv ?? 0, filmes = cats.filmes ?? 0, series = cats.series ?? 0;
        const groups = data.by_group || {};
        const groupsList = Object.entries(groups).slice(0,6).map(([g,c]) => `${g}: ${c}`).join(' · ');
        if (summaryEl) summaryEl.textContent = `TV: ${tv} | Filmes: ${filmes} | Séries: ${series}` + (groupsList ? ` — Grupos: ${groupsList}` : '');
      } catch (e) {
        if (loadingEl) loadingEl.innerHTML = '<span class=\"error\">' + (e?.message || e) + '</span>';
      }
    }
  </script>
  </head>
  <body>
    <div class=\"navbar\">
      <div class=\"brand\"><div class=\"logo\" aria-label=\"Logo robô\"><svg viewBox=\"0 0 24 24\" role=\"img\" aria-hidden=\"true\"><rect x=\"5\" y=\"7\" width=\"14\" height=\"10\" rx=\"3\"></rect><circle cx=\"9\" cy=\"12\" r=\"1.6\"></circle><circle cx=\"15\" cy=\"12\" r=\"1.6\"></circle><rect x=\"11\" y=\"3\" width=\"2\" height=\"3\"></rect></svg></div><strong>WEB Player JCTV</strong></div>
      <div class=\"tabs\">
        <a class=\"tab\" href=\"/ui/catalog\">Catálogo</a>
        <a class=\"tab active\" href=\"/ui/devices\">Dispositivos</a>
        <a class=\"tab\" href=\"/ui/capacity\">Capacidade</a>
      </div>
      <div class=\"nav-actions\"><a class=\"btn\" href=\"/ui/home\">← Voltar</a></div>
    </div>
    <div class=\"container\">
      <h1>Meus Dispositivos</h1>
      <div class=\"row\">
        <div class=\"col\">
          <div class=\"card\">
            <h2>Autenticação</h2>
            <p>Faça login e o token será usado nas chamadas abaixo.</p>
            <label>Usuário</label>
            <input id=\"username\" type=\"email\" value=\"admin@example.com\" />
            <label>Senha</label>
            <input id=\"password\" type=\"password\" value=\"admin123\" />
            <div class=\"toolbar\" style=\"margin-top:12px; display:flex; gap:10px;\">
              <button id=\"loginBtn\">Entrar</button>
              <div id=\"loginStatus\" class=\"muted\" style=\"align-self:center;\"></div>
            </div>
          </div>
        </div>
        <div class=\"col\">
          <div class=\"card\">
            <h2>Listar</h2>
            <div class=\"toolbar\" style=\"display:flex; gap:10px; align-items:center;\">
              <button id=\"listBtn\">Atualizar lista</button>
              <span class=\"muted\">Itens vinculados à sua conta</span>
            </div>
            <ul id=\"list\"></ul>
          </div>
        </div>
      </div>
      <div class=\"card\">
        <h2>Registrar novo</h2>
        <label>Fingerprint</label>
        <input id=\"fp\" placeholder=\"ex.: device-123\" />
        <label>Nome</label>
        <input id=\"name\" placeholder=\"ex.: Minha TV\" />
        <label>Plataforma</label>
        <input id=\"platform\" placeholder=\"ex.: web\" />
        <div class=\"toolbar\" style=\"margin-top:10px; display:flex; gap:10px;\">
          <button id=\"registerBtn\">Registrar</button>
          <div id=\"registerStatus\" class=\"muted\" style=\"align-self:center;\"></div>
        </div>
      </div>
      <div class=\"card\">
        <h2>Minhas Listas (M3U/HLS/EPG)</h2>
        <p>Cadastre suas listas e EPG. Ative uma para uso preferencial.</p>
        <label>Nome</label>
        <input id=\"pl_name\" placeholder=\"ex.: Lista Principal\" />
        <label>Tipo</label>
        <select id=\"pl_type\" style=\"width: 220px; padding: 12px; border-radius: 10px; background: rgba(14,14,18,0.8); color:#fff; border: 2px solid rgba(255,255,255,0.15);\">
          <option value=\"m3u\">M3U</option>
          <option value=\"hls\">HLS</option>
        </select>
        <label>URL da lista</label>
        <input id=\"pl_url\" placeholder=\"https://.../minha-lista.m3u\" />
        <label>URL do EPG (opcional)</label>
        <input id=\"pl_epg\" placeholder=\"https://.../guia.xml\" />
        <div class=\"toolbar\" style=\"margin-top:10px; display:flex; gap:10px; align-items:center;\">
          <button id=\"pl_save\">Salvar lista</button>
          <button id=\"pl_reload\">Atualizar</button>
          <div id=\"pl_status\" class=\"muted\" style=\"align-self:center;\"></div>
        </div>
        <div id=\"pl_list\" style=\"margin-top: 14px;\"></div>
      </div>
    </div>
    <script>
      qs('loginBtn').addEventListener('click', login);
      qs('listBtn').addEventListener('click', listDevices);
      qs('registerBtn').addEventListener('click', registerDevice);
      qs('pl_save').addEventListener('click', createPlaylist);
      qs('pl_reload').addEventListener('click', listPlaylists);
      // Restaurar sessão se já houver token salvo
      try {
        const existing = localStorage.getItem('access_token');
        if (existing) {
          token = existing;
          const st = qs('loginStatus'); if (st) st.textContent = 'Sessão ativa';
          listDevices();
          listPlaylists();
        }
      } catch {}
    </script>
  </body>
</html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/login")
def ui_login():
    html = """
<!DOCTYPE html>
<html lang=\"pt-BR\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Login</title>
  <style>
    :root {
      --bg1: #0b0d18; --bg2: #260b17; --tile: #821a1a; --tile-hover: #9c1f1f; --text: #e7e7e7; --muted:#bdbdbd;
    }
    html, body { height: 100%; }
    body {
      margin: 0; color: var(--text);
      font-family: "Segoe UI", Roboto, Arial, sans-serif;
      background: radial-gradient(1200px 600px at 20% 15%, var(--bg2), var(--bg1));
      display: grid; place-items: center;
    }
    .card {
      width: 360px; background: rgba(20,20,26,0.65); border: 1px solid rgba(255,255,255,0.08);
      border-radius: 12px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .brand { display:flex; align-items:center; gap:10px; margin-bottom: 10px; }
    .brand .logo {
      width: 28px; height: 28px; background: var(--tile); border-radius: 3px; display:grid; place-items:center; color:#fff;
      font-weight: 700; font-size: 12px;
    }
    .brand .logo svg { width: 20px; height: 20px; fill:#fff; }
    h1 { font-size: 20px; margin: 0 0 6px; }
    p { margin: 0 0 14px; color: var(--muted); }
    label { display:block; font-size: 13px; margin: 10px 0 6px; color: var(--muted); }
    input { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.15); background: rgba(14,14,18,0.8); color:#fff; box-sizing: border-box; }
    input[type="email"], input[type="password"] { height: 42px; }
    input[type="checkbox"] { width: 16px; height: 16px; margin: 0; }
    .pwd-wrap { position: relative; width: 100%; display: block; }
    .pwd-wrap input { 
      padding-right: 45px; 
      background: rgba(14,14,18,0.8); 
      border: 1px solid rgba(255,255,255,0.15);
    }
    /* Olho DENTRO do campo de senha */
    .eye { 
      position: absolute; 
      right: 8px; 
      top: 50%; 
      transform: translateY(-50%); 
      background: transparent; 
      border: none; 
      cursor: pointer; 
      padding: 6px; 
      width: 30px; 
      height: 30px; 
      display: flex; 
      align-items: center; 
      justify-content: center;
      z-index: 2;
      border-radius: 3px;
      margin: 0;
    }
    .eye:hover { background: rgba(255,255,255,0.08); }
    .eye:active { background: rgba(255,255,255,0.15); }
    .eye svg { width: 16px; height: 16px; fill: rgba(255,255,255,0.8); pointer-events: none; }
    /* Checkbox alinhado à esquerda */
    .remember { display:inline-flex; align-items:center; gap:8px; margin-top: 10px; font-size: 13px; color: var(--muted); }
    button { width: 100%; margin-top: 14px; background: var(--tile); color:#fff; border:none; border-radius:10px; padding: 12px; font-weight:600; cursor:pointer; }
    button:hover { background: var(--tile-hover); }
    .status { margin-top: 10px; min-height: 24px; font-size: 13px; }
    .err { color: #ff8c8c; }
  </style>
  <script>
    const API = location.origin; // mesmo host do backend
    function rid(){ return 'rid-' + Math.random().toString(36).slice(2); }
    function token(){ return localStorage.getItem('access_token'); }
    async function login() {
      const u = document.getElementById('username').value.trim();
      const p = document.getElementById('password').value;
      const remember = document.getElementById('remember').checked;
      const statusEl = document.getElementById('status');
      statusEl.textContent = 'Entrando...';
      try {
        const r = await fetch(API + '/auth/login', {
          method: 'POST', headers: { 'Content-Type':'application/json', 'X-Request-ID': rid() },
          body: JSON.stringify({ username: u, password: p })
        });
        if (!r.ok) throw new Error('Falha no login: ' + r.status);
        const data = await r.json();
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token || '');
        if (remember) {
          localStorage.setItem('remember_login', 'true');
          localStorage.setItem('saved_username', u);
          localStorage.setItem('saved_password', p);
        } else {
          localStorage.removeItem('remember_login');
          localStorage.removeItem('saved_username');
          localStorage.removeItem('saved_password');
        }
        statusEl.textContent = 'Login realizado';
        location.href = '/ui/home';
      } catch (e) {
        statusEl.innerHTML = "<span class='err'>" + (e?.message || e) + "</span>";
      }
    }
    function applyRememberDefaults() {
      const remember = localStorage.getItem('remember_login') === 'true';
      const u = document.getElementById('username');
      const p = document.getElementById('password');
      const rememberEl = document.getElementById('remember');
      if (rememberEl) rememberEl.checked = remember;
      if (remember) {
        const su = localStorage.getItem('saved_username') || '';
        const sp = localStorage.getItem('saved_password') || '';
        if (su) u.value = su;
        if (sp) p.value = sp;
      }
      if (!u.value) u.value = 'admin@example.com';
      if (!p.value) p.value = 'admin123';
    }
    addEventListener('DOMContentLoaded', () => {
      if (token()) { location.href = '/ui/home'; return; }
      document.getElementById('loginBtn').addEventListener('click', login);
      const toggle = document.getElementById('togglePwd');
      function updateEyeIcon(){
        const ip = document.getElementById('password');
        const eyeOpenSvg = '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>';
        const eyeClosedSvg = '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/></svg>';
        toggle.innerHTML = ip.type === 'password' ? eyeOpenSvg : eyeClosedSvg;
      }
      if (toggle) {
        toggle.addEventListener('click', () => {
          const ip = document.getElementById('password');
          ip.type = ip.type === 'password' ? 'text' : 'password';
          updateEyeIcon();
        });
        updateEyeIcon();
      }
      applyRememberDefaults();
    });
  </script>
</head>
<body>
  <div class="card">
    <div class="brand">
      <div class="logo" aria-label="Logo robô">
        <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
          <rect x="5" y="7" width="14" height="10" rx="3"></rect>
          <circle cx="9" cy="12" r="1.6"></circle>
          <circle cx="15" cy="12" r="1.6"></circle>
          <rect x="11" y="3" width="2" height="3"></rect>
        </svg>
      </div>
      <strong>WEB Player JCTV</strong>
    </div>
    <h1>Login</h1>
    <p>Entre para acessar TV ao vivo, filmes, séries e mais.</p>
    <label for="username">Usuário</label>
    <input id="username" type="email" placeholder="seu@email.com" />
    <label for="password">Senha</label>
    <div class="pwd-wrap">
      <input id="password" type="password" placeholder="••••••" />
      <button id="togglePwd" class="eye" type="button" aria-label="Mostrar senha"></button>
    </div>
    <label class="remember"><input type="checkbox" id="remember" /> Salvar login</label>
    <button id="loginBtn">Entrar</button>
    <div id="status" class="status"></div>
  </div>
</body>
</html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/home")
def ui_home():
    html = """
<!DOCTYPE html>
<html lang=\"pt-BR\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Home</title>
  <style>
    :root {
      --bg1:#0b0d18; --bg2:#260b17; --tile:#821a1a; --tile-hover:#9c1f1f; --text:#eee; --muted:#bdbdbd;
    }
    html, body { height: 100%; }
    body { margin:0; color:var(--text); font-family:"Segoe UI", Roboto, Arial, sans-serif;
      background: radial-gradient(1200px 600px at 20% 15%, var(--bg2), var(--bg1)); }
    .topbar { display:flex; justify-content:center; align-items:center; padding:16px 24px; color:var(--muted); text-align:center; }
    .brand { display:flex; align-items:center; gap:10px; justify-content:center; }
    .brand .logo { width:28px; height:28px; background:var(--tile); border-radius:3px; display:grid; place-items:center; color:#fff; font-weight:700; font-size:12px; }
    .brand .logo svg { width:20px; height:20px; fill:#fff; }
    .brand strong { color: var(--text); }
    .playlist-status { margin-left: 12px; color: var(--muted); }
    .page { display:grid; place-items:center; min-height: calc(100vh - 72px); }
    .grid { 
      display:grid; 
      grid-template-columns: 260px 180px 180px 180px; 
      grid-template-rows: 120px 120px 120px; 
      gap:16px; 
      margin: 0 auto; 
      padding: 30px 24px; 
      width: fit-content; 
    }
    .tile { background: rgba(30,12,16,0.6); border: 2px solid var(--tile); border-radius: 14px; display:flex; align-items:center; justify-content:center; flex-direction:column; cursor:pointer; transition: all .15s; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
    .tile:hover { background: rgba(40,14,18,0.7); border-color: var(--tile-hover); transform: translateY(-2px); }
    .tile.big { grid-row: span 2; }
    .label { margin-top:8px; font-weight:600; }
    .muted { color: var(--muted); }
    .footer { position: fixed; bottom: 8px; right: 12px; color: var(--muted); font-size: 12px; }
    svg { width:42px; height:42px; fill:#fff; }
  </style>
  <script>
    const API = location.origin;
    function rid(){ return 'rid-' + Math.random().toString(36).slice(2); }
    function token(){ return localStorage.getItem('access_token'); }
    function requireAuth(){ if(!token()) location.href = '/ui/login'; }
    async function reloadPlaylist(){ location.reload(); }
    async function exitApp(){ localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); location.href = '/ui/login'; }
    async function prefetchCatalog(){
      const statusEl = document.querySelector('.playlist-status');
      if (statusEl) statusEl.textContent = 'Preparando catálogo...';
      try {
        const r = await fetch('/catalog/channels/enriched/me', { headers: { 'Authorization': 'Bearer ' + token() } });
        await r.json();
        if (statusEl) statusEl.textContent = 'Catálogo pronto';
      } catch (e) {
        if (statusEl) statusEl.textContent = 'Falha ao preparar catálogo';
      }
    }
    addEventListener('DOMContentLoaded', async () => {
      requireAuth();
      // Exemplo: exibir expiração (placeholder)
      document.getElementById('playlistExpires').textContent = 'unlimited';
      // Pré-carregar catálogo para reduzir latência no primeiro uso
      try { await prefetchCatalog(); } catch {}
      // Navegação
      document.getElementById('live').onclick = () => location.href = '/ui/catalog?tab=live';
      document.getElementById('movies').onclick = () => location.href = '/ui/catalog?tab=movies';
      document.getElementById('series').onclick = () => location.href = '/ui/catalog?tab=series';
      document.getElementById('account').onclick = () => location.href = '/ui/devices';
      document.getElementById('settings').onclick = () => alert('Configurações: em desenvolvimento');
      document.getElementById('reload').onclick = reloadPlaylist;
      document.getElementById('exit').onclick = exitApp;
      document.getElementById('playlist').onclick = () => alert('Trocar playlist: em desenvolvimento');
    });
  </script>
</head>
<body>
  <div class="topbar">
    <div class="brand">
      <div class="logo" aria-label="Logo robô">
        <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
          <rect x="5" y="7" width="14" height="10" rx="3"></rect>
          <circle cx="9" cy="12" r="1.6"></circle>
          <circle cx="15" cy="12" r="1.6"></circle>
          <rect x="11" y="3" width="2" height="3"></rect>
        </svg>
      </div>
      <strong>WEB Player JCTV</strong>
      <span class="playlist-status">Current playlist expires: <span id="playlistExpires" class="muted">...</span></span>
    </div>
  </div>
  <div class="page">
    <div class="grid">
    <div id="live" class="tile big">
      <svg viewBox="0 0 24 24"><path d="M20 7H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h6l-2 2h8l-2-2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2zm0 9H4V9h16v7z"/></svg>
      <div class="label">Live</div>
    </div>
    <div id="movies" class="tile">
      <svg viewBox="0 0 24 24"><path d="M4 4h16v2H4zm0 4h16v12H4z"/></svg>
      <div class="label">Movies</div>
    </div>
    <div id="series" class="tile">
      <svg viewBox="0 0 24 24"><path d="M3 5h18v4H3zm0 6h18v8H3z"/></svg>
      <div class="label">Series</div>
    </div>
    <div id="settings" class="tile">
      <svg viewBox="0 0 24 24"><path d="M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8zm8.94 4a7.97 7.97 0 0 0-.47-2l2.02-1.57-2-3.46-2.46 1A8.03 8.03 0 0 0 16 3.53L15.5 1h-7L8 3.53a8.03 8.03 0 0 0-2.03 1.94l-2.46-1-2 3.46L3.53 10a7.97 7.97 0 0 0 0 4l-2.02 1.57 2 3.46 2.46-1A8.03 8.03 0 0 0 8 20.47L8.5 23h7l.5-2.53a8.03 8.03 0 0 0 2.03-1.94l2.46 1 2-3.46-2.02-1.57c.31-.96.47-1.98.47-3z"/></svg>
      <div class="label">Settings</div>
    </div>
    <div id="account" class="tile">
      <svg viewBox="0 0 24 24"><path d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5zm0 2c-4.33 0-8 2.17-8 5v1h16v-1c0-2.83-3.67-5-8-5z"/></svg>
      <div class="label">Account</div>
    </div>
    <div id="playlist" class="tile">
      <svg viewBox="0 0 24 24"><path d="M3 4h14v2H3zm0 4h14v2H3zm0 4h9v2H3zm13 1v7h2v-5h3v-2z"/></svg>
      <div class="label">Change Playlist</div>
    </div>
    <div id="reload" class="tile">
      <svg viewBox="0 0 24 24"><path d="M13 3a9 9 0 1 0 8.94 7h-2.07A7 7 0 1 1 12 5a6.93 6.93 0 0 1 4.9 2H13V3z"/></svg>
      <div class="label">Reload</div>
    </div>
    <div id="exit" class="tile">
      <svg viewBox="0 0 24 24"><path d="M10 2h4v4h-4zM5 8h14v12H5zM12 12v6"/></svg>
      <div class="label">EXIT</div>
    </div>
    </div>
  </div>
  <div class="footer">v3.65</div>
</body>
</html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/audit")
def ui_audit():
    html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Auditoria</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; }
    .box { border: 1px solid #ccc; padding: 1rem; margin-top: 1rem; border-radius: 6px; }
    input { padding: 0.5rem; width: 320px; }
    button { padding: 0.6rem 1rem; margin-top: 0.5rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
    th { background: #f7f7f7; }
  </style>
  </head>
  <body>
    <h1>Auditoria</h1>
    <div class="box">
      <h2>Autenticação</h2>
      <label>Usuário</label>
      <input id="username" type="email" value="admin@example.com" />
      <label>Senha</label>
      <input id="password" type="password" value="admin123" />
      <button id="loginBtn">Entrar</button>
      <div id="loginStatus"></div>
    </div>
    <div class="box">
      <h2>Logs</h2>
      <button id="loadBtn">Carregar meus eventos</button>
      <table>
        <thead>
          <tr>
            <th>Data</th><th>Ação</th><th>Recurso</th><th>Detalhes</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
    <script>
      let token = null;
      const qs = id => document.getElementById(id);

      async function login() {
        qs('loginStatus').textContent = 'Autenticando...';
        try {
          const resp = await fetch('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: qs('username').value, password: qs('password').value }) });
          if (!resp.ok) throw new Error('Falha no login: ' + resp.status);
          const data = await resp.json(); token = data.access_token; qs('loginStatus').textContent = 'Logado';
        } catch (e) { qs('loginStatus').textContent = (e?.message || e); }
      }

      async function loadLogs() {
        if (!token) return;
        const resp = await fetch('/audit/me?limit=50', { headers: { 'Authorization': 'Bearer ' + token } });
        const data = await resp.json();
        qs('rows').innerHTML = Array.isArray(data) && data.length
          ? data.map(i => `<tr><td>${i.created_at || ''}</td><td>${i.action || ''}</td><td>${i.resource || ''}</td><td>${i.details || ''}</td></tr>`).join('')
          : '<tr><td colspan="4">Nenhum evento</td></tr>';
      }

      qs('loginBtn').addEventListener('click', login);
      qs('loadBtn').addEventListener('click', loadLogs);
    </script>
  </body>
  </html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")
