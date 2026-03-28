// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  source: null,
  category: null,
  q: '',
  offset: 0,
  limit: 20,
  loading: false,
  totalLoaded: 0,
};

// ── Theme ─────────────────────────────────────────────────────────────────────
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ai-news-theme', theme);
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === theme);
  });
}

function initTheme() {
  const saved = localStorage.getItem('ai-news-theme') || 'light';
  setTheme(saved);
}

// ── Relative time ─────────────────────────────────────────────────────────────
function relativeTime(isoString) {
  if (!isoString) return '';
  const diff = (Date.now() - new Date(isoString).getTime()) / 1000;
  if (diff < 60) return 'hace un momento';
  if (diff < 3600) return `hace ${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)}h`;
  return `hace ${Math.floor(diff / 86400)}d`;
}

// ── HTML escaping ─────────────────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── Card rendering ────────────────────────────────────────────────────────────
function renderCard(article) {
  const isEmail = article.source_type === 'email';
  const sourceBadgeClass = isEmail ? 'badge-email' : 'badge-source';
  const summaryText = article.ai_summary || 'Procesando...';
  const summaryClass = article.ai_summary ? '' : 'pending';
  // Only allow http/https URLs — block javascript: and other schemes
  const rawUrl = String(article.url || '');
  const url = /^https?:\/\//i.test(rawUrl) ? escapeHtml(rawUrl) : '#';

  return `
    <div class="card">
      <div class="card-header">
        <span class="badge ${sourceBadgeClass}">${escapeHtml(article.source)}</span>
        <span class="card-time">${relativeTime(article.published_at)}</span>
      </div>
      <div class="card-title">${escapeHtml(article.title)}</div>
      <div class="card-summary ${summaryClass}">
        ${article.ai_summary ? '✨ ' : '⏳ '}${escapeHtml(summaryText)}
      </div>
      <div class="card-footer">
        <span class="badge badge-category">${escapeHtml(article.category_id || '—')}</span>
        ${url !== '#' ? `<a class="read-link" href="${url}" target="_blank" rel="noopener noreferrer">Leer más →</a>` : ''}
      </div>
    </div>
  `;
}

// ── Fetch articles ────────────────────────────────────────────────────────────
async function fetchArticles(append = false) {
  if (state.loading) return;
  state.loading = true;

  const params = new URLSearchParams({
    limit: state.limit,
    offset: state.offset,
  });
  if (state.source) params.set('source', state.source);
  if (state.category) params.set('category', state.category);
  if (state.q) params.set('q', state.q);

  try {
    const res = await fetch(`/api/articles?${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const articles = await res.json();

    const grid = document.getElementById('cards-grid');
    const errorEl = document.getElementById('error-msg');
    errorEl.style.display = 'none';

    if (!append) grid.innerHTML = '';

    if (articles.length === 0 && !append) {
      grid.innerHTML = '<div class="empty-state">No se encontraron artículos.</div>';
      stopPolling();
    } else {
      grid.insertAdjacentHTML('beforeend', articles.map(renderCard).join(''));
      state.totalLoaded = append ? state.totalLoaded + articles.length : articles.length;
      state.offset += articles.length;

      // Start polling if there are pending articles
      if (!append) {
        const pending = countPending(articles);
        if (pending > 0) {
          startPolling(pending);
        } else {
          stopPolling();
        }
      }
    }

    const btn = document.getElementById('load-more-btn');
    btn.style.display = articles.length === state.limit ? 'inline-block' : 'none';

    updateFooter();
  } catch (e) {
    const errorEl = document.getElementById('error-msg');
    errorEl.textContent = 'No se pudo cargar el contenido. Intentá de nuevo más tarde.';
    errorEl.style.display = 'block';
  } finally {
    state.loading = false;
  }
}

function loadMore() {
  fetchArticles(true);
}

// ── Filters ───────────────────────────────────────────────────────────────────
function resetPagination() {
  state.offset = 0;
  state.totalLoaded = 0;
}

function buildChips(containerId, items, activeKey, onSelect) {
  const container = document.getElementById(containerId);
  const allChip = `<span class="chip active" data-val="">Todas</span>`;
  const chips = items.map(item => {
    const val = typeof item === 'string' ? item : item.id;
    const label = typeof item === 'string' ? item : item.name;
    return `<span class="chip" data-val="${val}">${label}</span>`;
  });
  container.innerHTML = [allChip, ...chips].join('');

  container.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      onSelect(chip.dataset.val || null);
      resetPagination();
      fetchArticles();
    });
  });
}

async function initFilters() {
  const [sourcesRes, catsRes] = await Promise.all([
    fetch('/api/sources'),
    fetch('/api/categories'),
  ]);
  const sources = await sourcesRes.json();
  const categories = await catsRes.json();

  buildChips('source-filters', sources, 'source', val => { state.source = val; });
  buildChips('category-filters', categories, 'category', val => { state.category = val; });
}

// ── Search ────────────────────────────────────────────────────────────────────
let searchTimeout;
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('search-input').addEventListener('input', e => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.q = e.target.value.trim();
      resetPagination();
      fetchArticles();
    }, 300);
  });
});

// ── Footer ────────────────────────────────────────────────────────────────────
function updateFooter() {
  document.getElementById('footer-info').textContent =
    `${state.totalLoaded} artículos cargados`;
}

// ── Toast notification ─────────────────────────────────────────────────────
function showToast(message) {
  let toast = document.getElementById('summary-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'summary-toast';
    toast.className = 'toast';
    toast.innerHTML = `
      <span class="toast-icon">✨</span>
      <span id="toast-msg"></span>
      <button class="toast-close" onclick="dismissToast()" aria-label="Cerrar">×</button>
    `;
    document.body.appendChild(toast);
  }
  document.getElementById('toast-msg').textContent = message;
  toast.classList.add('toast-visible');
  // Auto-dismiss after 6 seconds
  clearTimeout(toast._dismissTimer);
  toast._dismissTimer = setTimeout(dismissToast, 6000);
}

function dismissToast() {
  const toast = document.getElementById('summary-toast');
  if (toast) toast.classList.remove('toast-visible');
}

// ── Polling for completed summaries ───────────────────────────────────────
let _pollInterval = null;
let _pendingCount = 0;

function countPending(articles) {
  return articles.filter(a => !a.is_processed).length;
}

async function checkSummaries() {
  try {
    const params = new URLSearchParams({ limit: state.limit, offset: 0 });
    if (state.source) params.set('source', state.source);
    if (state.category) params.set('category', state.category);
    if (state.q) params.set('q', state.q);

    const res = await fetch(`/api/articles?${params}`);
    if (!res.ok) return;
    const articles = await res.json();

    const nowPending = countPending(articles);

    if (nowPending < _pendingCount) {
      const processed = _pendingCount - nowPending;
      _pendingCount = nowPending;

      // Refresh the grid silently and notify
      resetPagination();
      await fetchArticles();
      showToast(`${processed} resumen${processed > 1 ? 'es listos' : ' listo'} — recargado`);

      if (_pendingCount === 0) stopPolling();
    } else {
      _pendingCount = nowPending;
    }
  } catch {
    // Silent — polling failures don't disrupt UX
  }
}

function startPolling(initialPendingCount) {
  _pendingCount = initialPendingCount;
  if (_pollInterval) return;
  _pollInterval = setInterval(checkSummaries, 30000); // every 30s
}

function stopPolling() {
  if (_pollInterval) {
    clearInterval(_pollInterval);
    _pollInterval = null;
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  initTheme();
  await initFilters();
  await fetchArticles();
}

init();
