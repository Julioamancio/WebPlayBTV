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
    }
    /* Navbar com abas e busca */
    .navbar { 
      display: grid; grid-template-columns: 240px 1fr 380px; align-items: center;
      padding: 12px 20px; background: linear-gradient(0deg, rgba(20,20,26,0.40), rgba(20,20,26,0.55));
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .brand { display: flex; align-items: center; gap: 10px; }
    .brand .logo {
      width: 28px; height: 28px; background: var(--tile); border-radius: 3px; 
      display: grid; place-items: center; color: #fff; font-weight: 700; font-size: 12px;
    }
    .brand .logo svg { width: 20px; height: 20px; fill: #fff; }
    .brand strong { font-size: 16px; }
    .tabs { display: flex; gap: 18px; align-items: center; }
    .tab { color: var(--muted); font-weight: 600; cursor: pointer; padding: 8px 0; }
    .tab.active { color: #fff; border-bottom: 2px solid var(--tile); }
    .searchbar { display: flex; gap: 10px; justify-content: flex-end; }
    .searchbar input { width: 240px; padding: 8px 12px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.15); background: rgba(14,14,18,0.8); color: #fff; }
    .searchbar select { padding: 8px 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.15); background: rgba(14,14,18,0.8); color: #fff; }
    /* Layout com sidebar */
    .layout { display: grid; grid-template-columns: 280px 1fr; gap: 24px; }
    .sidebar { padding: 18px; border-right: 1px solid rgba(255,255,255,0.08); }
    .sidebar .section { margin-bottom: 16px; }
    .sidebar .item { display:flex; align-items:center; justify-content: space-between; padding: 10px 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.12); color: var(--muted); cursor: pointer; }
    .sidebar .item:hover { color: #fff; border-color: rgba(255,255,255,0.18); }
    .sidebar .item .dot { width: 8px; height: 8px; background: var(--tile); border-radius: 50%; }
    /* Área de conteúdo */
    .container { padding: 24px; }
    .toolbar { display:flex; align-items:center; gap: 12px; margin-bottom: 10px; }
    .toolbar button { padding: 8px 16px; background: var(--tile); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; }
    .toolbar button:hover { background: var(--tile-hover); }
    .grid { 
      display: grid; 
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
      gap: 16px; 
      margin-top: 16px; 
    }
    .card { 
      background: rgba(20,20,26,0.65); 
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 12px; 
      padding: 16px; 
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      transition: all 0.2s ease;
    }
    .card:hover { 
      border-color: rgba(255,255,255,0.15);
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }
    .channel-header { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
    .logo-wrap { width: 48px; height: 48px; display: grid; place-items: center; }
    .channel-logo-img { width: 48px; height: 48px; object-fit: contain; border-radius: 6px; }
    .channel-logo { 
      width: 48px; height: 48px; border-radius: 6px;
      background: rgba(255,255,255,0.05); border: 1px dashed rgba(255,255,255,0.2);
      position: relative; overflow: hidden;
    }
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
    .channel-info h3 { margin: 0; font-size: 16px; color: var(--text); }
    .channel-info .badges { margin-top: 4px; }
    .badge { 
      display: inline-block; padding: 2px 8px; border-radius: 12px; 
      background: rgba(130,26,26,0.3); color: var(--muted); 
      font-size: 11px; margin-right: 6px; border: 1px solid rgba(130,26,26,0.5);
    }
    .program-info { margin: 12px 0; font-size: 13px; color: var(--muted); }
    .program-info .current { color: var(--text); font-weight: 500; }
    .stream-link { 
      display: inline-block; padding: 6px 12px; background: var(--tile); 
      color: #fff; text-decoration: none; border-radius: 6px; font-size: 12px;
      font-weight: 600; transition: background 0.2s;
    }
    .stream-link:hover { background: var(--tile-hover); }
    .empty-state { 
      text-align: center; padding: 48px 24px; color: var(--muted);
      background: rgba(20,20,26,0.4); border-radius: 12px; margin-top: 24px;
    }
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
      </aside>
      <main class="container">
        <h1 style="margin: 0 0 8px; font-size: 24px;">Catálogo de Canais</h1>
        <p style="margin: 0; color: var(--muted);">Navegue pelos canais disponíveis e acesse transmissões ao vivo.</p>
        <div class="toolbar">
          <button id="reload">Recarregar</button>
        </div>
        <div id="grid" class="grid"></div>
      </main>
    </div>
    <script>
      const grid = document.getElementById('grid');
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
      let currentCategory = 'live';
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

      async function loadChannels() {
        showSkeleton(8);
        try {
          const resp = await fetch('/catalog/channels/enriched');
          const data = await resp.json();
          channels = Array.isArray(data) ? data : [];
          try {
            const groups = Array.from(new Set(channels.map(c => c.group).filter(Boolean))).sort((a,b) => String(a).localeCompare(String(b)));
            groupFilter.innerHTML = '<option value="">todos os grupos</option>' + groups.map(g => `<option value="${String(g).toLowerCase()}">${String(g)}</option>`).join('');
          } catch(e) { console.warn('falha ao popular grupos', e); }
          render();
        } catch (e) {
          grid.innerHTML = '<div class="empty-state">❌ Erro ao carregar canais: ' + (e?.message || e) + '</div>';
        }
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
          if (currentCategory === 'live') return true;
          if (currentCategory === 'movies') return group.includes('filme') || group.includes('movie');
          if (currentCategory === 'series') return group.includes('série') || group.includes('series');
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
                <div class=\"channel-logo ${c.logo ? 'hidden' : ''}\"></div>
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
            <a href=\"${c.url}\" target=\"_blank\" class=\"stream-link\">▶️ Assistir ao vivo</a>
          </div>
        `).join('');
      }

      reload.addEventListener('click', loadChannels);
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
    </script>
  </body>
</html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/devices")
def ui_devices():
    html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Meus Dispositivos</title>
  <style>
    :root { --bg1:#0b0d18; --bg2:#260b17; --tile:#821a1a; --tile-hover:#9c1f1f; --text:#eee; --muted:#bdbdbd; }
    html, body { height: 100%; margin:0; }
    body { color: var(--text); font-family: "Segoe UI", Roboto, Arial, sans-serif;
      background: radial-gradient(1200px 600px at 20% 15%, var(--bg2), var(--bg1)); }
    .topbar { display:flex; justify-content:center; align-items:center; padding:16px 24px; color:var(--muted); text-align:center; border-bottom: 1px solid rgba(255,255,255,0.08); }
    .brand { display:flex; align-items:center; gap:10px; justify-content:center; }
    .brand .logo { width:28px; height:28px; background:var(--tile); border-radius:3px; display:grid; place-items:center; color:#fff; font-weight:700; font-size:12px; }
    .brand .logo svg { width:20px; height:20px; fill:#fff; }
    .brand strong { color: var(--text); }
    .page { display:grid; place-items:center; min-height: calc(100vh - 72px); }
    .content { width: fit-content; margin: 0 auto; padding: 24px; }
    .card { width: 100%; max-width: 560px; background: rgba(20,20,26,0.65); border: 1px solid rgba(255,255,255,0.08);
      border-radius: 12px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 16px; }
    h1 { font-size: 22px; margin: 0 0 12px; }
    h2 { font-size: 18px; margin: 0 0 10px; }
    p { margin: 0 0 12px; color: var(--muted); }
    label { display:block; font-size: 13px; margin: 10px 0 6px; color: var(--muted); }
    input { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.15); background: rgba(14,14,18,0.8); color:#fff; box-sizing: border-box; }
    button { padding: 10px 16px; background: var(--tile); color:#fff; border:none; border-radius:8px; cursor:pointer; font-weight:600; }
    button:hover { background: var(--tile-hover); }
    ul { padding-left: 1.25rem; margin: 6px 0 0; }
    li { margin-bottom: 0.25rem; }
    .error { color: #f07; font-weight: bold; }
    /* Responsividade dispositivos */
    @media (max-width: 768px) {
      .content { padding: 16px; }
      .card { padding: 16px; }
      h1 { font-size: 20px; }
      h2 { font-size: 16px; }
    }
    @media (max-width: 480px) {
      .topbar { padding: 12px 16px; }
      .content { padding: 12px; }
      input { padding: 8px 10px; }
      button { padding: 8px 12px; }
    }
  </style>
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
      </div>
    </div>
    <div class="page">
      <div class="content">
        <h1>Meus Dispositivos</h1>

        <div class="card">
          <h2>Autenticação</h2>
          <p>Faça login e o token será usado nas chamadas abaixo.</p>
          <label>Usuário</label>
          <input id="username" type="email" value="admin@example.com" />
          <label>Senha</label>
          <input id="password" type="password" value="admin123" />
          <div style="margin-top:10px; display:flex; gap:10px;">
            <button id="loginBtn">Entrar</button>
            <div id="loginStatus" style="align-self:center;"></div>
          </div>
        </div>

        <div class="card">
          <h2>Listar</h2>
          <div style="display:flex; gap:10px; align-items:center;">
            <button id="listBtn">Atualizar lista</button>
            <span style="color:var(--muted);">Itens vinculados à sua conta</span>
          </div>
          <ul id="list"></ul>
        </div>

        <div class="card">
          <h2>Registrar novo</h2>
          <label>Fingerprint</label>
          <input id="fp" placeholder="ex.: device-123" />
          <label>Nome</label>
          <input id="name" placeholder="ex.: Minha TV" />
          <label>Plataforma</label>
          <input id="platform" placeholder="ex.: web" />
          <div style="margin-top:10px; display:flex; gap:10px;">
            <button id="registerBtn">Registrar</button>
            <div id="registerStatus" style="align-self:center;"></div>
          </div>
        </div>
      </div>
    </div>

    <script>
      let token = null;
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
          qs('loginStatus').textContent = 'Logado';
        } catch (e) {
          qs('loginStatus').innerHTML = '<span class="error">' + (e?.message || e) + '</span>';
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
          qs('registerStatus').innerHTML = '<span class="error">' + (e?.message || e) + '</span>';
        }
      }

      qs('loginBtn').addEventListener('click', login);
      qs('listBtn').addEventListener('click', listDevices);
      qs('registerBtn').addEventListener('click', registerDevice);
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
    addEventListener('DOMContentLoaded', async () => {
      requireAuth();
      // Exemplo: exibir expiração (placeholder)
      document.getElementById('playlistExpires').textContent = 'unlimited';
      // Navegação
      document.getElementById('live').onclick = () => location.href = '/ui/catalog';
      document.getElementById('movies').onclick = () => alert('Filmes: em desenvolvimento');
      document.getElementById('series').onclick = () => alert('Séries: em desenvolvimento');
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
