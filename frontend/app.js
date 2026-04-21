// ════════════════════════════════════════════════════════════════════════════
// AI News Hub 2.0 — app.js
// ════════════════════════════════════════════════════════════════════════════

// ── Utilities ────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function relativeTime(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)    return 'hace un momento';
  if (diff < 3600)  return `hace ${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)}h`;
  return `hace ${Math.floor(diff / 86400)}d`;
}

function formatDateSpanish(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const days   = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
  const months = ['enero','febrero','marzo','abril','mayo','junio',
                  'julio','agosto','septiembre','octubre','noviembre','diciembre'];
  return `${days[d.getDay()]}, ${d.getDate()} de ${months[d.getMonth()]} de ${d.getFullYear()}`;
}

function safeUrl(raw) {
  const u = String(raw || '');
  return /^https?:\/\//i.test(u) ? escapeHtml(u) : '#';
}

function renderSkeletons(count = 6) {
  return Array.from({ length: count }, () => `
    <div class="skeleton-card">
      <div class="skeleton-line short"></div>
      <div class="skeleton-line title long"></div>
      <div class="skeleton-line medium"></div>
      <div class="skeleton-line long"></div>
      <div class="skeleton-line short"></div>
    </div>
  `).join('');
}

// ── Theme ─────────────────────────────────────────────────────────────────────
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ai-news-theme', theme);
  document.querySelectorAll('.theme-btn').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.theme === theme)
  );
}
function initTheme() { setTheme(localStorage.getItem('ai-news-theme') || 'light'); }

// ── Sidebar ───────────────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebar-overlay').classList.toggle('open');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-overlay').classList.remove('open');
}

// ── Navigation ────────────────────────────────────────────────────────────────
let currentView = 'home';
const VIEW_INIT = {};  // view initializers registry

function navigateTo(view) {
  if (currentView === view && view !== 'dashboard') return; // allow dashboard refresh
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n =>
    n.classList.toggle('active', n.dataset.view === view)
  );
  const el = document.getElementById(`view-${view}`);
  if (el) el.classList.add('active');
  currentView = view;
  closeSidebar();
  if (VIEW_INIT[view]) VIEW_INIT[view]();
}

// ── Shared data cache ─────────────────────────────────────────────────────────
let sourcesCache = null;
let categoriesCache = null;

async function loadSharedData() {
  try {
    const [sRes, cRes] = await Promise.all([fetch('/api/sources'), fetch('/api/categories')]);
    sourcesCache   = await sRes.json();
    categoriesCache = await cRes.json();
  } catch (e) {
    sourcesCache   = [];
    categoriesCache = [];
  }
}

function getCategoryName(id) {
  if (!id) return '—';
  const cat = (categoriesCache || []).find(c => c.id === id);
  return cat ? cat.name : id;
}

// ── Article card (shared renderer) ───────────────────────────────────────────
function renderCard(article) {
  const isEmail = article.source_type === 'email';
  const url     = safeUrl(article.url);
  const summary = article.ai_summary || 'Procesando resumen...';
  const summaryClass = article.ai_summary ? '' : 'pending';
  const catName = getCategoryName(article.category_id);

  return `
    <div class="card">
      <div class="card-header">
        <span class="badge ${isEmail ? 'badge-email' : 'badge-source'}">${escapeHtml(article.source)}</span>
        <span class="card-time">${relativeTime(article.published_at)}</span>
      </div>
      <div class="card-title">${escapeHtml(article.title)}</div>
      <div class="card-summary ${summaryClass}">
        ${article.ai_summary ? '✨ ' : '⏳ '}${escapeHtml(summary)}
      </div>
      <div class="card-footer">
        <span class="badge badge-category">${escapeHtml(catName)}</span>
        ${url !== '#' ? `<a class="read-link" href="${url}" target="_blank" rel="noopener noreferrer">Leer más →</a>` : ''}
      </div>
    </div>`;
}

// ── Chip builder ──────────────────────────────────────────────────────────────
function buildChips(containerId, items, onSelect, { multi = false, selected = null } = {}) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const allChip = multi ? '' : `<span class="chip ${selected === null ? 'active' : ''}" data-val="">Todas</span>`;
  const chips = items.map(item => {
    const val   = typeof item === 'string' ? item : item.id;
    const label = typeof item === 'string' ? item : item.name;
    const isActive = multi
      ? (Array.isArray(selected) && selected.includes(val))
      : (selected === val);
    return `<span class="chip ${isActive ? 'active' : ''}" data-val="${escapeHtml(val)}">${escapeHtml(label)}</span>`;
  });

  container.innerHTML = [allChip, ...chips].join('');

  container.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      if (multi) {
        chip.classList.toggle('active');
        const active = [...container.querySelectorAll('.chip.active')].map(c => c.dataset.val).filter(Boolean);
        onSelect(active);
      } else {
        container.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        onSelect(chip.dataset.val || null);
      }
    });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// ── INICIO VIEW ──────────────────────────────────────────────────────────────
// ════════════════════════════════════════════════════════════════════════════
const homeState = {
  source: null, category: null, q: '',
  offset: 0, limit: 20, loading: false, totalLoaded: 0,
  initialized: false,
};

function initHomeView() {
  if (homeState.initialized) return;
  homeState.initialized = true;

  buildChips('home-source-filters',   sourcesCache,    v => { homeState.source   = v; homeState.offset = 0; homeState.totalLoaded = 0; fetchHomeArticles(); });
  buildChips('home-category-filters', categoriesCache, v => { homeState.category = v; homeState.offset = 0; homeState.totalLoaded = 0; fetchHomeArticles(); });

  const input = document.getElementById('home-search');
  let searchTimer;
  input.addEventListener('input', e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      homeState.q = e.target.value.trim();
      homeState.offset = 0; homeState.totalLoaded = 0;
      fetchHomeArticles();
    }, 300);
  });

  fetchHomeArticles();
}

async function fetchHomeArticles(append = false) {
  if (homeState.loading) return;
  homeState.loading = true;

  const grid    = document.getElementById('home-grid');
  const errorEl = document.getElementById('home-error');
  if (!append) grid.innerHTML = renderSkeletons(6);

  const params = new URLSearchParams({ limit: homeState.limit, offset: homeState.offset });
  if (homeState.source)   params.set('source',   homeState.source);
  if (homeState.category) params.set('category', homeState.category);
  if (homeState.q)        params.set('q',        homeState.q);

  try {
    const res      = await fetch(`/api/articles?${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const articles = await res.json();

    errorEl.style.display = 'none';
    if (!append) grid.innerHTML = '';

    if (articles.length === 0 && !append) {
      grid.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><div>No se encontraron artículos con estos filtros.</div></div>`;
      stopPolling();
    } else {
      grid.insertAdjacentHTML('beforeend', articles.map(renderCard).join(''));
      homeState.totalLoaded = append ? homeState.totalLoaded + articles.length : articles.length;
      homeState.offset += articles.length;
      if (!append) {
        const pending = articles.filter(a => !a.is_processed).length;
        pending > 0 ? startPolling(pending) : stopPolling();
      }
    }

    const btn = document.getElementById('home-load-more');
    btn.style.display = articles.length === homeState.limit ? 'inline-block' : 'none';
    document.getElementById('home-footer').textContent =
      homeState.totalLoaded > 0 ? `${homeState.totalLoaded} artículos cargados` : '';
  } catch (e) {
    grid.innerHTML = '';
    errorEl.textContent = 'No se pudo cargar el contenido. Intentá de nuevo más tarde.';
    errorEl.style.display = 'block';
  } finally {
    homeState.loading = false;
  }
}

function loadMore() { fetchHomeArticles(true); }

// ════════════════════════════════════════════════════════════════════════════
// ── DASHBOARD VIEW ───────────────────────────────────────────────────────────
// ════════════════════════════════════════════════════════════════════════════
let chartInstances = {};

function destroyCharts() {
  Object.values(chartInstances).forEach(c => { try { c.destroy(); } catch (e) {} });
  chartInstances = {};
}

async function initDashboardView() {
  document.getElementById('dashboard-stats').innerHTML = renderSkeletons(4)
    .replace(/cards-grid/g, 'stats-grid');
  destroyCharts();

  try {
    const res   = await fetch('/api/stats');
    if (!res.ok) throw new Error();
    const stats = await res.json();
    renderStatCards(stats);
    renderDailyChart(stats.articles_per_day);
    renderCategoryChart(stats.by_category);
    renderSourcesChart(stats.by_source);
  } catch (e) {
    document.getElementById('dashboard-stats').innerHTML =
      `<div class="error-msg">No se pudieron cargar las estadísticas.</div>`;
  }
}

function renderStatCards(stats) {
  const cards = [
    { icon: '📰', label: 'Total artículos',  value: stats.total.toLocaleString('es') },
    { icon: '📅', label: 'Hoy',              value: stats.today.toLocaleString('es') },
    { icon: '📆', label: 'Esta semana',      value: stats.this_week.toLocaleString('es') },
    { icon: '✅', label: 'Procesados',       value: `${stats.processed_pct}%` },
  ];
  document.getElementById('dashboard-stats').innerHTML = cards.map(c => `
    <div class="stat-card">
      <span class="stat-icon">${c.icon}</span>
      <div class="stat-value">${c.value}</div>
      <div class="stat-label">${c.label}</div>
    </div>`).join('');
}

function getChartColors() {
  const theme = document.documentElement.getAttribute('data-theme');
  if (theme === 'dark')     return { accent: '#58a6ff', grid: 'rgba(255,255,255,0.06)', text: '#8b949e', palette: ['#58a6ff','#3fb950','#f78166','#d2a8ff','#ffa657','#79c0ff','#56d364'] };
  if (theme === 'gradient') return { accent: '#a78bfa', grid: 'rgba(167,139,250,0.1)',  text: '#a78bfa', palette: ['#a78bfa','#818cf8','#c084fc','#e879f9','#f472b6','#38bdf8','#34d399'] };
  return { accent: '#6366f1', grid: 'rgba(0,0,0,0.06)', text: '#9ca3af', palette: ['#6366f1','#8b5cf6','#ec4899','#f59e0b','#10b981','#3b82f6','#ef4444'] };
}

function renderDailyChart(data) {
  const ctx = document.getElementById('chart-daily').getContext('2d');
  const { accent, grid, text } = getChartColors();

  // Gradient fill
  const gradient = ctx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0, accent.replace(')', ', 0.3)').replace('rgb', 'rgba').replace('#', 'rgba(').replace('rgba(', 'rgba(') + (accent.startsWith('#') ? '' : ''));
  // Simpler gradient using hex
  gradient.addColorStop(0, accent + '44');
  gradient.addColorStop(1, accent + '00');

  chartInstances.daily = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.label),
      datasets: [{
        label: 'Artículos',
        data: data.map(d => d.count),
        borderColor: accent,
        backgroundColor: gradient,
        borderWidth: 2.5,
        pointBackgroundColor: accent,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true,
        tension: 0.4,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: grid }, ticks: { color: text, font: { size: 11 } } },
        y: { grid: { color: grid }, ticks: { color: text, font: { size: 11 }, stepSize: 1 }, beginAtZero: true },
      },
    },
  });
}

function renderCategoryChart(data) {
  const ctx = document.getElementById('chart-categories').getContext('2d');
  const { palette, text } = getChartColors();

  const labels = data.map(d => getCategoryName(d.id));
  const values = data.map(d => d.count);

  chartInstances.categories = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: palette, borderWidth: 0 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: text, font: { size: 11 }, boxWidth: 12, padding: 10 },
        },
      },
      cutout: '65%',
    },
  });
}

function renderSourcesChart(data) {
  const ctx = document.getElementById('chart-sources').getContext('2d');
  const { accent, grid, text, palette } = getChartColors();

  chartInstances.sources = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.name),
      datasets: [{
        label: 'Artículos',
        data: data.map(d => d.count),
        backgroundColor: palette,
        borderRadius: 6,
        borderWidth: 0,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: grid }, ticks: { color: text, font: { size: 11 } }, beginAtZero: true },
        y: { grid: { display: false }, ticks: { color: text, font: { size: 11 } } },
      },
    },
  });
}

// ════════════════════════════════════════════════════════════════════════════
// ── RESUMEN DEL DÍA VIEW ─────────────────────────────────────────────────────
// ════════════════════════════════════════════════════════════════════════════
async function initDigestView() {
  const content = document.getElementById('digest-content');
  const dateLabel = document.getElementById('digest-date-label');

  const today = new Date();
  dateLabel.textContent = formatDateSpanish(today.toISOString());
  content.innerHTML = `<div class="cards-grid">${renderSkeletons(6)}</div>`;

  const dateFrom = today.toISOString().slice(0, 10);

  try {
    const res = await fetch(`/api/articles?limit=100&date_from=${dateFrom}&sort=desc`);
    if (!res.ok) throw new Error();
    const articles = await res.json();

    if (articles.length === 0) {
      content.innerHTML = `<div class="empty-state">
        <div class="empty-icon">🌅</div>
        <div>Todavía no hay artículos para hoy.</div>
        <div style="font-size:12px;margin-top:8px;">El feed se actualiza cada 2 horas.</div>
      </div>`;
      return;
    }

    // Group by category
    const groups = {};
    articles.forEach(a => {
      const key = a.category_id || 'otros';
      if (!groups[key]) groups[key] = [];
      groups[key].push(a);
    });

    const catIcons = { modelos: '🤖', agentes: '⚙️', plugins: '🔌', webdesign: '🎨', creatividad: '✨', investigacion: '🔬', otros: '📌' };

    let html = '';
    Object.entries(groups).forEach(([catId, arts]) => {
      const catName = getCategoryName(catId);
      const icon    = catIcons[catId] || '📰';
      const shown   = arts.slice(0, 4);
      html += `
        <div class="digest-section">
          <div class="digest-section-header">
            <span style="font-size:18px">${icon}</span>
            <span class="digest-section-title">${escapeHtml(catName)}</span>
            <span class="digest-count">${arts.length} artículo${arts.length !== 1 ? 's' : ''}</span>
          </div>
          <div class="digest-grid">${shown.map(renderCard).join('')}</div>
        </div>`;
    });
    content.innerHTML = html;
  } catch (e) {
    content.innerHTML = `<div class="error-msg">No se pudo cargar el resumen del día.</div>`;
  }
}

// ════════════════════════════════════════════════════════════════════════════
// ── BÚSQUEDA AVANZADA VIEW ───────────────────────────────────────────────────
// ════════════════════════════════════════════════════════════════════════════
const searchState = {
  source: null, category: null, q: '',
  dateFrom: '', dateTo: '', sort: 'desc',
  offset: 0, limit: 20, initialized: false,
};

function initSearchView() {
  if (searchState.initialized) return;
  searchState.initialized = true;

  buildChips('adv-source-filters',   sourcesCache,    v => { searchState.source   = v; });
  buildChips('adv-category-filters', categoriesCache, v => { searchState.category = v; });
}

async function performSearch(append = false) {
  const grid    = document.getElementById('search-grid');
  const info    = document.getElementById('search-results-info');
  const loadBtn = document.getElementById('search-load-more');

  if (!append) {
    searchState.offset = 0;
    searchState.q        = document.getElementById('adv-search-input').value.trim();
    searchState.dateFrom = document.getElementById('adv-date-from').value;
    searchState.dateTo   = document.getElementById('adv-date-to').value;
    searchState.sort     = document.getElementById('adv-sort').value;
    grid.innerHTML = `<div class="cards-grid">${renderSkeletons(6)}</div>`;
    info.style.display = 'none';
  }

  const params = new URLSearchParams({ limit: searchState.limit, offset: searchState.offset, sort: searchState.sort });
  if (searchState.q)        params.set('q',         searchState.q);
  if (searchState.source)   params.set('source',    searchState.source);
  if (searchState.category) params.set('category',  searchState.category);
  if (searchState.dateFrom) params.set('date_from', searchState.dateFrom);
  if (searchState.dateTo)   params.set('date_to',   searchState.dateTo);

  try {
    const res      = await fetch(`/api/articles?${params}`);
    if (!res.ok) throw new Error();
    const articles = await res.json();

    if (!append) grid.innerHTML = '';

    if (articles.length === 0 && !append) {
      grid.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><div>No se encontraron resultados.</div></div>`;
      loadBtn.style.display = 'none';
      info.style.display    = 'none';
    } else {
      grid.insertAdjacentHTML('beforeend', articles.map(renderCard).join(''));
      searchState.offset += articles.length;
      info.textContent = append ? '' : `${articles.length < searchState.limit ? articles.length : '20+'} resultados encontrados`;
      info.style.display = append ? 'none' : 'block';
      loadBtn.style.display = articles.length === searchState.limit ? 'inline-block' : 'none';
    }
  } catch (e) {
    grid.innerHTML = `<div class="error-msg">Error al buscar. Intentá de nuevo.</div>`;
  }
}

function loadMoreSearch() { performSearch(true); }

// ════════════════════════════════════════════════════════════════════════════
// ── MI FEED VIEW ─────────────────────────────────────────────────────────────
// ════════════════════════════════════════════════════════════════════════════
const myfeedState = {
  selectedSources: [],
  selectedCategories: [],
  allArticles: [],
  displayed: 0,
  pageSize: 18,
  initialized: false,
};

const MYFEED_KEY = 'ai-news-myfeed-prefs';

function loadMyFeedPrefs() {
  try { return JSON.parse(localStorage.getItem(MYFEED_KEY) || 'null'); } catch { return null; }
}

function initMyFeedView() {
  const prefs = loadMyFeedPrefs();

  if (prefs && (prefs.sources.length || prefs.categories.length)) {
    myfeedState.selectedSources    = prefs.sources;
    myfeedState.selectedCategories = prefs.categories;
    showMyFeedArticles();
  } else {
    buildMyFeedSetup();
  }
}

function buildMyFeedSetup() {
  document.getElementById('myfeed-setup').style.display    = 'block';
  document.getElementById('myfeed-articles').style.display = 'none';

  const prefs = loadMyFeedPrefs() || { sources: [], categories: [] };
  myfeedState.selectedSources    = [...prefs.sources];
  myfeedState.selectedCategories = [...prefs.categories];

  buildChips('myfeed-source-chips', sourcesCache, v => { myfeedState.selectedSources = v; }, {
    multi: true, selected: myfeedState.selectedSources,
  });
  buildChips('myfeed-category-chips', categoriesCache, v => { myfeedState.selectedCategories = v; }, {
    multi: true, selected: myfeedState.selectedCategories,
  });
}

function saveMyFeedPrefs() {
  if (!myfeedState.selectedSources.length && !myfeedState.selectedCategories.length) {
    showToast('Elegí al menos una fuente o categoría 👆');
    return;
  }
  localStorage.setItem(MYFEED_KEY, JSON.stringify({
    sources:    myfeedState.selectedSources,
    categories: myfeedState.selectedCategories,
  }));
  showMyFeedArticles();
}

function editMyFeedPrefs() { buildMyFeedSetup(); }

async function showMyFeedArticles() {
  document.getElementById('myfeed-setup').style.display    = 'none';
  document.getElementById('myfeed-articles').style.display = 'block';

  const grid    = document.getElementById('myfeed-grid');
  const loadBtn = document.getElementById('myfeed-load-more');
  grid.innerHTML = renderSkeletons(6);
  loadBtn.style.display = 'none';

  // Build prefs summary
  const srcNames  = myfeedState.selectedSources;
  const catNames  = myfeedState.selectedCategories.map(id => getCategoryName(id));
  const summaryEl = document.getElementById('myfeed-prefs-summary');
  const srcText   = srcNames.length  ? `<strong>${srcNames.join(', ')}</strong>` : '<em>todas las fuentes</em>';
  const catText   = catNames.length  ? `<strong>${catNames.join(', ')}</strong>` : '<em>todas las categorías</em>';
  summaryEl.innerHTML = `Mostrando: ${srcText} · ${catText}`;

  try {
    // Fetch from each selected source in parallel; if none selected, fetch all
    let articles = [];

    if (myfeedState.selectedSources.length > 0) {
      const calls = myfeedState.selectedSources.map(src =>
        fetch(`/api/articles?limit=40&source=${encodeURIComponent(src)}&sort=desc`)
          .then(r => r.ok ? r.json() : [])
          .catch(() => [])
      );
      const results = await Promise.all(calls);
      articles = results.flat();
    } else {
      const r = await fetch('/api/articles?limit=80&sort=desc');
      articles = r.ok ? await r.json() : [];
    }

    // Filter by selected categories client-side
    if (myfeedState.selectedCategories.length > 0) {
      articles = articles.filter(a => myfeedState.selectedCategories.includes(a.category_id));
    }

    // Deduplicate by id, sort by date desc
    const seen = new Set();
    articles = articles
      .filter(a => { if (seen.has(a.id)) return false; seen.add(a.id); return true; })
      .sort((a, b) => new Date(b.published_at) - new Date(a.published_at));

    myfeedState.allArticles = articles;
    myfeedState.displayed   = 0;

    grid.innerHTML = '';

    if (articles.length === 0) {
      grid.innerHTML = `<div class="empty-state"><div class="empty-icon">⭐</div><div>No hay artículos con tus preferencias actuales.</div></div>`;
      return;
    }

    renderMyFeedPage();
  } catch (e) {
    grid.innerHTML = `<div class="error-msg">No se pudo cargar tu feed. Intentá de nuevo.</div>`;
  }
}

function renderMyFeedPage() {
  const grid    = document.getElementById('myfeed-grid');
  const loadBtn = document.getElementById('myfeed-load-more');
  const slice   = myfeedState.allArticles.slice(myfeedState.displayed, myfeedState.displayed + myfeedState.pageSize);
  grid.insertAdjacentHTML('beforeend', slice.map(renderCard).join(''));
  myfeedState.displayed += slice.length;
  loadBtn.style.display = myfeedState.displayed < myfeedState.allArticles.length ? 'inline-block' : 'none';
}

function loadMoreMyFeed() { renderMyFeedPage(); }

// ════════════════════════════════════════════════════════════════════════════
// ── COMPARAR VIEW ────────────────────────────────────────────────────────────
// ════════════════════════════════════════════════════════════════════════════
function initCompareView() {
  const results = document.getElementById('compare-results');
  if (!results.hasChildNodes()) {
    results.innerHTML = `
      <div class="compare-intro">
        <div class="compare-intro-icon">⚖️</div>
        <p>Ingresá un término de búsqueda para ver qué dicen distintas fuentes sobre el mismo tema.</p>
      </div>`;
  }
}

async function performCompare() {
  const input   = document.getElementById('compare-input');
  const results = document.getElementById('compare-results');
  const q       = input.value.trim();
  if (!q) { input.focus(); return; }

  results.innerHTML = `<div class="cards-grid">${renderSkeletons(6)}</div>`;

  try {
    const res      = await fetch(`/api/articles?limit=80&q=${encodeURIComponent(q)}&sort=desc`);
    if (!res.ok) throw new Error();
    const articles = await res.json();

    if (articles.length === 0) {
      results.innerHTML = `<div class="empty-state"><div class="empty-icon">🔎</div><div>No se encontraron artículos para "<strong>${escapeHtml(q)}</strong>".</div></div>`;
      return;
    }

    // Group by source
    const grouped = {};
    articles.forEach(a => {
      if (!grouped[a.source]) grouped[a.source] = [];
      grouped[a.source].push(a);
    });

    const totalSources = Object.keys(grouped).length;
    let html = `<div class="compare-no-results">${articles.length} artículos de ${totalSources} fuente${totalSources !== 1 ? 's' : ''} para "<strong>${escapeHtml(q)}</strong>"</div>`;
    html += `<div class="compare-columns">`;

    Object.entries(grouped)
      .sort((a, b) => b[1].length - a[1].length)
      .forEach(([source, arts]) => {
        html += `
          <div class="compare-column">
            <div class="compare-column-header">
              <span class="compare-source-name">${escapeHtml(source)}</span>
              <span class="compare-count">${arts.length} artículo${arts.length !== 1 ? 's' : ''}</span>
            </div>
            <div class="compare-cards">
              ${arts.slice(0, 5).map(a => {
                const url = safeUrl(a.url);
                return `<div class="compare-card">
                  <div class="compare-card-title">${escapeHtml(a.title)}</div>
                  ${a.ai_summary ? `<div class="compare-card-summary">✨ ${escapeHtml(a.ai_summary)}</div>` : ''}
                  <div class="compare-card-meta">
                    <span class="compare-card-time">${relativeTime(a.published_at)}</span>
                    ${url !== '#' ? `<a class="read-link" href="${url}" target="_blank" rel="noopener noreferrer">Leer →</a>` : ''}
                  </div>
                </div>`;
              }).join('')}
            </div>
          </div>`;
      });

    html += `</div>`;
    results.innerHTML = html;
  } catch (e) {
    results.innerHTML = `<div class="error-msg">Error al comparar. Intentá de nuevo.</div>`;
  }
}

// ════════════════════════════════════════════════════════════════════════════
// ── TOAST ─────────────────────────────────────────────────────────────────────
// ════════════════════════════════════════════════════════════════════════════
let _toastTimer = null;

function showToast(message) {
  const toast = document.getElementById('toast');
  document.getElementById('toast-msg').textContent = message;
  toast.classList.add('toast-visible');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(dismissToast, 6000);
}

function dismissToast() {
  document.getElementById('toast').classList.remove('toast-visible');
}

// ── Polling for completed summaries ──────────────────────────────────────────
let _pollInterval = null;
let _pendingCount = 0;

async function checkSummaries() {
  try {
    const params = new URLSearchParams({ limit: homeState.limit, offset: 0 });
    if (homeState.source)   params.set('source',   homeState.source);
    if (homeState.category) params.set('category', homeState.category);
    if (homeState.q)        params.set('q',        homeState.q);

    const res      = await fetch(`/api/articles?${params}`);
    if (!res.ok) return;
    const articles = await res.json();
    const nowPending = articles.filter(a => !a.is_processed).length;

    if (nowPending < _pendingCount) {
      const done = _pendingCount - nowPending;
      _pendingCount = nowPending;
      homeState.offset = 0; homeState.totalLoaded = 0;
      await fetchHomeArticles();
      showToast(`${done} resumen${done > 1 ? 'es listos' : ' listo'} — recargado ✨`);
      if (_pendingCount === 0) stopPolling();
    } else {
      _pendingCount = nowPending;
    }
  } catch { /* silent */ }
}

function startPolling(initial) {
  _pendingCount = initial;
  if (_pollInterval) return;
  _pollInterval = setInterval(checkSummaries, 30000);
}

function stopPolling() {
  if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }
}

// ════════════════════════════════════════════════════════════════════════════
// ── REGISTER VIEW INITIALIZERS & BOOT ────────────────────────────────────────
// ════════════════════════════════════════════════════════════════════════════
VIEW_INIT['home']      = initHomeView;
VIEW_INIT['dashboard'] = initDashboardView;
VIEW_INIT['digest']    = initDigestView;
VIEW_INIT['search']    = initSearchView;
VIEW_INIT['myfeed']    = initMyFeedView;
VIEW_INIT['compare']   = initCompareView;

async function init() {
  initTheme();
  await loadSharedData();
  navigateTo('home');
}

init();
