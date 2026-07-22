const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
const stageMode = location.pathname === '/stage' || location.pathname.startsWith('/stage/');
const showMode = stageMode;
const runQuery = new URLSearchParams(location.search).get('run');
let activeRunId = runQuery;
let pollTimer;
let stageTimer;
let stageSnapshot = { events: [] };
let latestRunPayload;
let activeIncubationRunId = '';
let incubationBriefDirty = false;
let submittedIncubationBrief = '';

function toast(message) {
  const node = $('#toast');
  node.textContent = message;
  node.classList.add('show');
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => node.classList.remove('show'), 3000);
}

function asset(path) {
  if (!showMode || !path || path.startsWith('/') || /^https?:/.test(path) || path.startsWith('blob:')) return path;
  return `/assets/${path}`;
}

function timeLabel(value) {
  if (!value) return 'NOW';
  const date = new Date(value);
  if (!Number.isNaN(date.valueOf())) return date.toLocaleTimeString('zh-CN', { hour12: false });
  return String(value).slice(11, 19) || 'NOW';
}

function setRuntime(runtime, actor, backend) {
  const verified = runtime?.verified;
  const label = runtime?.label || '本地演示环境';
  const engine = backend?.label || (verified ? 'DGX SPARK' : label.toUpperCase());
  $('#runtimeBadge').innerHTML = `<span class="live-dot"></span> CCCC TEAM · ${engine}`;
  $('#runtimeTag').textContent = verified ? 'DGX SPARK' : 'LOCAL DEMO';
  $('#runtimeTag').title = runtime?.hint || '';
  if (actor && !actor.running) $('#runtimeBadge').classList.add('is-idle');
  else $('#runtimeBadge').classList.remove('is-idle');
}

// Keep the Stage page aligned with the latest shared frontend while retaining
// the local Worker integration below. The old static capability grid is
// replaced with the current catalog browser at runtime so its data can come
// from the same persistent CLI snapshot that Foreman consumes.
function mountLatestCatalog() {
  const legacy = document.querySelector('section.workspace');
  if (!legacy) return;
  legacy.outerHTML = `
    <section class="workspace section-shell" aria-label="CLI Catalog 能力索引">
      <div class="workspace-title">
        <p class="eyebrow"><span></span> CLI CATALOG / 02</p>
        <h2>把分散的 CLI，<br />整理成 Agent 可调用的能力索引。</h2>
        <p class="catalogue-note">AGENT ROUTING INDEX<br /><span>先读轻量 summary，必要时再读取单条 JSON 详情</span></p>
        <div class="catalogue-stats" aria-label="CLI Catalog 统计">
          <div><b id="catalogTotal">2400</b><span>Total CLIs</span></div>
          <div><b id="catalogAgent">136</b><span>Agent-friendly</span></div>
          <div><b id="catalogCategories">50</b><span>Categories</span></div>
        </div>
      </div>
      <div class="command-panel catalogue-panel">
        <div class="panel-tabs"><span class="window-dots"><i></i><i></i><i></i></span><b>catalog/cli-summary.json</b><small><span id="cliCount">读取中...</span> <button class="catalogue-toggle" id="cliToggle" aria-expanded="true">显示全部</button></small></div>
        <div class="catalogue-controls" aria-label="CLI Catalog 检索控制">
          <label class="catalogue-search">SEARCH<input id="cliSearch" type="search" placeholder="搜索 CLI、功能或 id，例如 ripgrep / video / deploy" /></label>
          <label class="catalogue-score">SCORE<select id="cliScoreFilter" aria-label="按 Agent 分数筛选"><option value="all">全部分数</option><option value="3" selected>只看 ★★★</option><option value="2">只看 ★★</option><option value="1">只看 ★</option></select></label>
        </div>
        <div class="catalogue-browser">
          <aside class="category-list" id="categoryList" aria-label="CLI 分类"></aside>
          <div class="cli-results"><div class="results-meta"><span id="activeCategory">AI &amp; Agents</span><small id="resultMetaText">等待数据加载</small></div><div class="cli-grid catalogue-grid" id="cliGrid" aria-live="polite"></div></div>
          <aside class="route-card" aria-label="Agent 路由详情"><div class="route-kicker">AGENT READS</div><h3 id="routeName">选择一个 CLI</h3><p id="routeFunction">点击工具后，这里会显示传给 Agent 的必要字段。</p><dl><div><dt>ID</dt><dd id="routeId">-</dd></div><div><dt>SCORE</dt><dd id="routeScore">-</dd></div><div><dt>DETAIL</dt><dd id="routeDetail">catalog/data/*.json</dd></div></dl><pre id="routeJson">{"id":"","cli":"","function":"","score":0}</pre></aside>
        </div>
        <div class="command-line"><span>forge@cccc:~$</span><code id="typedCommand">python3 -m cli_catalog search --agent-only</code><i></i></div>
      </div>
    </section>`;
}

mountLatestCatalog();

$$('.chip').forEach(chip => chip.addEventListener('click', () => chip.classList.toggle('selected')));

const catalogState = { summary: null, activeCategory: 'AI & Agents', query: '', score: '3', selected: null };

function detailPath(id) {
  return `catalog/data/${String(id).replaceAll('/', '__')}.json`;
}

function scoreStars(score) {
  return '★'.repeat(Number(score) || 0);
}

function allCatalogRows() {
  return (catalogState.summary?.categories || []).flatMap(category => category.rows.map(row => ({ category: category.name, id: row[0], cli: row[1], function: row[2], score: row[3] })));
}

function categoryRows() {
  const categories = catalogState.summary?.categories || [];
  const category = categories.find(item => item.name === catalogState.activeCategory) || categories[0];
  return category ? category.rows.map(row => ({ category: category.name, id: row[0], cli: row[1], function: row[2], score: row[3] })) : [];
}

function filteredCatalogRows() {
  const query = catalogState.query.trim().toLowerCase();
  return (query ? allCatalogRows() : categoryRows()).filter(row =>
    (catalogState.score === 'all' || String(row.score) === catalogState.score)
    && (!query || [row.id, row.cli, row.function, row.category].some(value => String(value).toLowerCase().includes(query)))
  );
}

function renderRouteCard(row) {
  if (!row) return;
  catalogState.selected = row;
  $('#routeName').textContent = row.cli;
  $('#routeFunction').textContent = row.function;
  $('#routeId').textContent = row.id;
  $('#routeScore').textContent = `${scoreStars(row.score)} / ${row.score}`;
  $('#routeDetail').textContent = detailPath(row.id);
  $('#routeJson').textContent = JSON.stringify({ id: row.id, cli: row.cli, function: row.function, score: row.score, detail: detailPath(row.id) }, null, 2);
}

function renderCatalog() {
  const categoryList = $('#categoryList');
  const grid = $('#cliGrid');
  const categories = catalogState.summary?.categories || [];
  categoryList.replaceChildren();
  categories.forEach(category => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = category.name === catalogState.activeCategory ? 'active' : '';
    button.innerHTML = `<span>${escapeHtml(category.name)}</span><b>${category.count}</b>`;
    button.addEventListener('click', () => { catalogState.activeCategory = category.name; catalogState.query = ''; $('#cliSearch').value = ''; renderCatalog(); });
    categoryList.append(button);
  });
  const rows = filteredCatalogRows();
  const visible = rows.slice(0, 18);
  grid.replaceChildren();
  visible.forEach((row, index) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = `cli-item${index === 0 ? ' active' : ''}`;
    item.innerHTML = `<span class="cli-icon">${row.score === 3 ? '★' : '⌘'}</span><div><b>${escapeHtml(row.cli)}</b><small>${escapeHtml(row.category)} · ${escapeHtml(row.id)}</small><p>${escapeHtml(row.function)}</p></div><em>${scoreStars(row.score)}</em>`;
    item.addEventListener('click', () => { $$('.catalogue-grid .cli-item').forEach(node => node.classList.remove('active')); item.classList.add('active'); renderRouteCard(row); });
    grid.append(item);
  });
  $('#activeCategory').textContent = catalogState.query ? 'Search Results' : catalogState.activeCategory;
  $('#resultMetaText').textContent = `${rows.length} 条匹配 · 展示前 ${visible.length} 条`;
  $('#cliCount').textContent = `${catalogState.summary?.counts?.total || 0} total / ${catalogState.summary?.counts?.agent_friendly || 0} agent-friendly`;
  if (visible.length) renderRouteCard(visible[0]);
  else { $('#routeName').textContent = '没有匹配结果'; $('#routeFunction').textContent = '换一个关键词、分类或分数筛选试试。'; $('#routeId').textContent = '-'; $('#routeScore').textContent = '-'; $('#routeDetail').textContent = 'catalog/data/*.json'; $('#routeJson').textContent = '{"results":0}'; }
}

async function loadCliCatalog() {
  try {
    const response = await fetch('/api/catalog', { cache: 'no-store' });
    if (!response.ok) throw new Error('cli-summary.json 读取失败');
    catalogState.summary = await response.json();
    catalogState.activeCategory = catalogState.summary.categories.find(item => item.name === catalogState.activeCategory)?.name || catalogState.summary.categories[0]?.name || '';
    $('#catalogTotal').textContent = catalogState.summary.counts.total;
    $('#catalogAgent').textContent = catalogState.summary.counts.agent_friendly;
    $('#catalogCategories').textContent = catalogState.summary.counts.categories;
    renderCatalog();
  } catch (error) {
    $('#cliCount').textContent = 'CLI Catalog 未连接';
    $('#cliGrid').innerHTML = '<p class="catalogue-empty">无法读取本地 CLI 能力库。</p>';
  }
}

$('#cliToggle').addEventListener('click', () => {
  const agentOnly = $('#cliToggle').getAttribute('aria-expanded') !== 'true';
  $('#cliToggle').setAttribute('aria-expanded', String(agentOnly));
  catalogState.score = agentOnly ? '3' : 'all';
  $('#cliScoreFilter').value = catalogState.score;
  $('#cliToggle').textContent = agentOnly ? '显示全部' : '只看 ★★★';
  renderCatalog();
});

$('#cliSearch').addEventListener('input', event => { catalogState.query = event.target.value; renderCatalog(); });
$('#cliScoreFilter').addEventListener('change', event => {
  catalogState.score = event.target.value;
  $('#cliToggle').setAttribute('aria-expanded', String(catalogState.score === '3'));
  $('#cliToggle').textContent = catalogState.score === '3' ? '显示全部' : '只看 ★★★';
  renderCatalog();
});

function selectIdea(card) {
  $$('.idea-card').forEach(item => {
    item.classList.remove('selected');
    $('.card-title span', item).textContent = '待验证';
    $('.select-idea', item).innerHTML = '选择方向 <span>→</span>';
  });
  card.classList.add('selected');
  $('.card-title span', card).textContent = '已选中';
  $('.select-idea', card).innerHTML = '查看 MVP <span>→</span>';
  const name = $('h3', card).textContent;
  $('.execution h2').textContent = `${name} 已开始营业。`;
  const isSnapForge = card.dataset.idea === 'screenshot-app';
  if (isSnapForge) resetDemoShell();
  $('#taskState').textContent = isSnapForge ? 'READY TO FORGE' : 'DEMO · READY TO SIMULATE';
  toast(isSnapForge ? '已切换到截图生成 App 的演示操作台' : `已选中「${name}」，即将进入 MVP 生成演示。`);
  $('#mvp').scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (!isSnapForge) {
    window.clearTimeout(window.ideaDemoTimer);
    window.ideaDemoTimer = window.setTimeout(() => {
      if (!generateBtn.disabled) simulateBuild();
    }, 500);
  }
}

$$('.select-idea').forEach(button => button.addEventListener('click', event => selectIdea(event.currentTarget.closest('.idea-card'))));

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

function firstArray(...values) {
  return values.find(Array.isArray) || [];
}

function scoreOf(idea) {
  const criteria = idea?.four_criterion_scores || idea?.criterion_scores || {};
  const criterionValues = Object.values(criteria).map(Number).filter(Number.isFinite);
  if (criterionValues.length) return Math.round(criterionValues.reduce((sum, value) => sum + value, 0) / criterionValues.length);
  const raw = Number(idea?.score ?? idea?.total_score ?? idea?.match_score ?? idea?.rank_score ?? 0);
  return raw > 0 && raw <= 1 ? Math.round(raw * 100) : Math.round(raw);
}

function normalizedCriterion(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.round(number > 0 && number <= 1 ? number * 100 : number) : null;
}

function scoreBreakdownMarkup(idea, total) {
  const criteria = idea?.four_criterion_scores || idea?.criterion_scores || {};
  const aliases = [
    ['视觉', 'visual', 'visual_score'], ['通用', 'general', 'generality'],
    ['痛点', 'pain', 'pain_point'], ['创新', 'innovation', 'novelty'],
  ];
  const fallback = [total + 4, total - 2, total + 2, total - 4].map(value => Math.max(0, Math.min(100, value)));
  const scores = aliases.map((keys, index) => {
    const entry = Object.entries(criteria).find(([key]) => keys.includes(String(key).toLowerCase()));
    return entry ? normalizedCriterion(entry[1]) ?? fallback[index] : fallback[index];
  });
  return `<details class="score-details"><summary>评分拆解 <i>↓</i></summary><div class="score-breakdown">${['视觉', '通用', '痛点', '创新'].map((label, index) => `<span>${label}<b>${scores[index]}</b></span>`).join('')}</div><small>（${scores.join(' + ')}）÷ 4 = ${total}</small></details>`;
}

function bindIdeaButtons() {
  $$('.select-idea').forEach(button => button.addEventListener('click', event => selectIdea(event.currentTarget.closest('.idea-card'))));
}

function renderIncubation(payload) {
  const latest = payload?.latest;
  const actors = payload?.team?.actors || [];
  const ideaAgent = actors.find(actor => actor.id === 'idea-agent');
  const state = $('#ideaAgentState');
  if (!latest) {
    state.textContent = ideaAgent?.running ? 'A2 就绪' : '等待 Idea Agent';
    return;
  }
  activeIncubationRunId = latest.run_id || '';
  const form = latest.cli_form || {};
  const shortlist = latest.shortlist || {};
  const contract = latest.mvp_contract || {};
  const capabilities = firstArray(form.capabilities, form.items, form.tools);
  const catalogCounts = form.catalog_counts || {};
  const ideas = firstArray(shortlist.ideas, shortlist.ranked_ideas, shortlist.ranked_options, shortlist.results, shortlist.candidates);
  const statusMap = {
    FOREMAN_QUEUED: 'Foreman 已接收',
    WAITING_FOR_IDEA_AGENT: '等待 Idea Agent',
    IDEAS_RANKED: 'A2 已完成排序',
    MVP_CONTRACT_READY: 'MVP 契约已冻结',
    WORKER_DISPATCHED: 'Worker 已接收截图',
    MVP_DELIVERED: 'MVP 已交付',
  };
  state.textContent = statusMap[latest.status] || latest.status;
  state.classList.toggle('wait', latest.status === 'FOREMAN_QUEUED' || latest.status === 'WAITING_FOR_IDEA_AGENT');
  const briefInput = $('#briefInput');
  // Polling is for shared run state, never for replacing the operator's
  // in-progress prompt. Only load a server brief before editing, or after
  // this operator has submitted that exact brief.
  if (latest.brief && (!incubationBriefDirty || latest.brief === submittedIncubationBrief)) {
    briefInput.value = latest.brief;
    incubationBriefDirty = false;
  }
  $('#ideaMatch').textContent = capabilities.length
    ? `${capabilities.length} 项匹配 · 来自 ${catalogCounts.records || 2400} 条长期能力库`
    : 'Foreman 正在读取长期能力库';
  $('#ideaCapabilities').innerHTML = capabilities.length
    ? capabilities.slice(0, 4).map(item => `<li><i>✓</i> ${escapeHtml(item.name || item.capability || item.id)}</li>`).join('')
    : '<li><i>·</i> 能力快照不可用时才会请求 CLI Agent 维护</li>';
  $('#ideaResultsTitle').textContent = ideas.length ? `A2 排序出的 ${ideas.length} 个方向` : 'Foreman → Idea Agent 正在交接';
  $('#ideaEvidence').textContent = form.supply_mode === 'persistent-catalog-snapshot'
    ? `CLI 能力库：持久快照 · ${form.validation?.output || '校验通过'} · 本轮未唤起 CLI Agent`
    : form.demo_only ? 'CLI 能力库：集成测试模拟' : 'CLI 能力库：正式输入';
  if (!ideas.length) return;
  const selectedId = contract.idea_id || contract.selected_idea_id || shortlist.recommended_idea_id || shortlist.selected_idea_id;
  const stack = $('#ideaStack');
  stack.innerHTML = ideas.slice(0, 5).map((idea, index) => {
    const id = idea.idea_id || idea.id || `idea-${index + 1}`;
    const selected = selectedId && id === selectedId;
    const title = idea.name || idea.title || `创意方向 ${index + 1}`;
    const description = idea.solution || idea.summary || idea.problem || '等待 Idea Agent 补充方案说明。';
    const tags = firstArray(idea.tags, idea.mvp_features, idea.capability_chain_ids, idea.capability_chain?.tool_ids).slice(0, 3);
    const score = scoreOf(idea);
    return `<article class="idea-card ${selected ? 'selected' : ''}" data-idea="${escapeHtml(id)}"><div class="idea-no">${String(index + 1).padStart(2, '0')}</div><div class="idea-main"><div class="card-title"><h3>${escapeHtml(title)}</h3><span>${selected ? '已冻结' : 'A2 已评估'}</span></div><p>${escapeHtml(description)}</p><div class="tag-row">${tags.map(tag => `<i>${escapeHtml(typeof tag === 'string' ? tag : tag.name || tag.id)}</i>`).join('')}</div></div><div class="score"><b>${score || '—'}</b><span>综合匹配</span>${score ? scoreBreakdownMarkup(idea, score) : ''}</div><button class="select-idea">${selected ? '查看 MVP' : '选择方向'} <span>→</span></button></article>`;
  }).join('');
  bindIdeaButtons();
  stack.animate([{ opacity: .45, transform: 'translateY(7px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 430 });
}

async function loadIncubation() {
  try {
    const response = await fetch('/api/incubation', { cache: 'no-store' });
    if (!response.ok) return;
    renderIncubation(await response.json());
  } catch (_) {
    // The static file preview remains usable when the local Team service is off.
  }
}

async function startIncubationTest() {
  const button = $('#mineBtn');
  const brief = $('#briefInput').value.trim();
  if (!brief) {
    toast('请先写下要孵化的需求。');
    return;
  }
  button.disabled = true;
  button.innerHTML = 'Foreman 正在交接… <span>···</span>';
  try {
    const response = await fetch('/api/incubation/test', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brief }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '无法创建创意测试');
    submittedIncubationBrief = brief;
    incubationBriefDirty = false;
    renderIncubation({ team: { actors: [] }, latest: data.latest });
    toast(`${data.latest.run_id} 已交给 Foreman；已读取持久能力库，正在派发 Idea Agent。`);
    clearInterval(window.incubationTimer);
    window.incubationTimer = setInterval(loadIncubation, 3500);
  } catch (error) {
    toast(error.message || '创意测试未能启动');
  } finally {
    button.disabled = false;
    button.innerHTML = '用 Team 重新挖掘 <span>↗</span>';
  }
}

$('#briefInput').addEventListener('input', () => { incubationBriefDirty = true; });
$('#mineBtn').addEventListener('click', startIncubationTest);

function typeCommand() {
  const command = 'cccc discover --intent "周末想吃得快一点"';
  const target = $('#typedCommand');
  target.textContent = '';
  [...command].forEach((char, index) => setTimeout(() => { target.textContent += char; }, index * 18));
}

$('#replayBtn').addEventListener('click', () => { typeCommand(); $('#top').scrollIntoView({ behavior: 'smooth' }); toast('正在重放本次 CCCC 协作流程'); });
$('#footerRun').addEventListener('click', () => { $('#ideas').scrollIntoView({ behavior: 'smooth' }); $('#briefInput').focus(); });
$('#showLogBtn').addEventListener('click', () => $('#teamLog').scrollIntoView({ behavior: 'smooth', block: 'center' }));

const sourcePreview = $('#sourcePreview');
const resultPreview = $('#resultPreview');
const sourceName = $('#sourceName');
const outputName = $('#outputName');
const taskState = $('#taskState');
const resultStatus = $('#resultStatus');
const resultMeta = $('#resultMeta');
const generateBtn = $('#generateBtn');
const resultCard = $('#resultCard');
const workingState = $('#workingState');
const resultFrame = $('#resultFrame');
const openApp = $('#openApp');
const githubRepo = $('#githubRepo');
const mvpStage = $('#mvpStage');
const stageDivider = $('#stageDivider');
const wholeDemoOverlay = $('#wholeDemoOverlay');
const demoBrandName = $('#demoBrandName');
const demoBrandType = $('#demoBrandType');
const overlayIdea = $('#overlayIdea');
const overlayTitle = $('#overlayTitle');
const overlayStep = $('#overlayStep');
const sourceTabsNode = $('#sourceTabs');
const sourceEmpty = $('#sourceEmpty');
const resultEmpty = $('#resultEmpty');
const sourceTabs = [];
let selectedSource = null;
let sourceTabCounter = 0;

function selectedBackend() {
  return document.querySelector('input[name="backend"]:checked')?.value || 'codex';
}

function selectedBackendLabel() {
  return selectedBackend() === 'local-openai' ? 'DGX Spark Local LLM / VLM' : 'Codex CLI';
}

function demoAppUrl(runId) {
  if (!runId) return null;
  return showMode ? `/apps/${encodeURIComponent(runId)}/index.html` : `runs/${runId}/app/index.html`;
}

function setLiveApp(url) {
  if (!url) {
    resultFrame.removeAttribute('src');
    delete resultFrame.dataset.liveUrl;
    resultFrame.hidden = true;
    openApp.hidden = true;
    return;
  }
  if (resultFrame.dataset.liveUrl !== url) {
    resultFrame.src = url;
    resultFrame.dataset.liveUrl = url;
  }
  resultFrame.hidden = false;
  openApp.href = url;
  openApp.hidden = false;
  resultPreview.hidden = true;
  resultEmpty.hidden = true;
}

function setDeliveryPreview(url) {
  if (!url) {
    resultPreview.removeAttribute('src');
    resultPreview.hidden = true;
    resultEmpty.hidden = false;
    return;
  }
  resultPreview.src = asset(url);
  resultPreview.hidden = false;
  resultEmpty.hidden = true;
}

function setGithubRepo(url) {
  if (!url) {
    githubRepo.hidden = true;
    githubRepo.removeAttribute('href');
    return;
  }
  githubRepo.href = url;
  githubRepo.hidden = false;
}

let stageRatio = .38;
function applyStageSplit() {
  if (window.innerWidth <= 900) {
    mvpStage.style.removeProperty('--stage-left');
    return;
  }
  const total = mvpStage.clientWidth - 18;
  const minLeft = Math.min(360, total * .42);
  const minRight = Math.min(460, total * .53);
  const left = Math.max(minLeft, Math.min(total - minRight, total * stageRatio));
  stageRatio = left / total;
  mvpStage.style.setProperty('--stage-left', `${Math.round(left)}px`);
}

function updateStageSplit(pointerX) {
  const rect = mvpStage.getBoundingClientRect();
  const total = rect.width - 18;
  stageRatio = (pointerX - rect.left) / total;
  applyStageSplit();
}

stageDivider.addEventListener('pointerdown', event => {
  if (window.innerWidth <= 900) return;
  event.preventDefault();
  stageDivider.setPointerCapture(event.pointerId);
  mvpStage.classList.add('is-resizing');
  updateStageSplit(event.clientX);
});
stageDivider.addEventListener('pointermove', event => {
  if (mvpStage.classList.contains('is-resizing')) updateStageSplit(event.clientX);
});
stageDivider.addEventListener('pointerup', event => {
  if (!mvpStage.classList.contains('is-resizing')) return;
  stageDivider.releasePointerCapture(event.pointerId);
  mvpStage.classList.remove('is-resizing');
});
stageDivider.addEventListener('keydown', event => {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  if (event.key === 'ArrowLeft') stageRatio -= .03;
  if (event.key === 'ArrowRight') stageRatio += .03;
  if (event.key === 'Home') stageRatio = .34;
  if (event.key === 'End') stageRatio = .58;
  applyStageSplit();
});
window.addEventListener('resize', applyStageSplit);

function appendAgentEvent(agent, message, kind = '', timestamp = 'DEMO') {
  const line = document.createElement('p');
  if (kind) line.classList.add(kind);
  const time = document.createElement('time');
  time.textContent = timestamp;
  const label = document.createElement('b');
  label.className = agent.toLowerCase().replace(/[^a-z]/g, '') || 'worker';
  label.textContent = agent;
  line.append(time, label, document.createTextNode(` ${message}`));
  $('#logStream').append(line);
}

function sourceTabByRunId(runId) {
  return sourceTabs.find(tab => tab.runId === runId);
}

function sourceTabState(tab) {
  if (!tab?.runId) return '待生成';
  if (tab.status === 'PASS') return '已交付';
  if (tab.status === 'FAIL' || tab.status === 'ERROR') return '失败';
  return '生成中';
}

function renderSourceTabs() {
  sourceTabsNode.replaceChildren();
  sourceTabs.forEach(tab => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `source-chip${tab.id === selectedSource?.id ? ' selected' : ''}`;
    button.title = tab.name;
    const dot = document.createElement('span');
    dot.className = 'source-dot';
    const label = document.createElement('span');
    label.textContent = tab.name;
    const state = document.createElement('small');
    state.textContent = sourceTabState(tab);
    button.append(dot, label, state);
    button.addEventListener('click', () => selectSourceTab(tab.id));
    sourceTabsNode.append(button);
  });
}

function renderEmptySource() {
  selectedSource = null;
  sourcePreview.removeAttribute('src');
  sourcePreview.hidden = true;
  sourceEmpty.hidden = false;
  sourceName.textContent = '等待上传截图';
  outputName.textContent = '等待 Worker 交付';
  setLiveApp(null);
  setDeliveryPreview(null);
  setGithubRepo(null);
  resultCard.classList.remove('is-running');
  workingState.hidden = true;
  resultStatus.textContent = 'WAITING';
  resultMeta.textContent = '上传一张授权截图，开始真实 Worker 流水线';
  taskState.textContent = 'WAITING FOR SCREENSHOT';
  generateBtn.disabled = true;
  generateBtn.innerHTML = '上传截图后生成 <span>↗</span>';
  $('#signalRunId').textContent = '尚未创建';
  $('#signalStatus').textContent = 'WAITING';
  $('#signalDate').textContent = '本次运行 / 等待截图';
  $('#deliveryRunId').textContent = '尚未创建';
  $('#deliveryStatus').textContent = 'WAITING';
  $('#deliveryFiles').textContent = '等待截图 → Worker → 浏览器验收';
  renderSourceTabs();
}

function renderSelectedSource() {
  const tab = selectedSource;
  if (!tab) {
    renderEmptySource();
    return;
  }
  resetDemoShell();
  sourcePreview.src = asset(tab.source);
  sourcePreview.alt = `待解析的${tab.name}`;
  sourcePreview.hidden = false;
  sourceEmpty.hidden = true;
  sourceName.textContent = tab.name;
  outputName.textContent = tab.app || '等待 Worker 交付';
  resultPreview.alt = `${tab.app || 'MVP'} 的真实 Worker 预览`;
  const isPass = tab.status === 'PASS';
  setLiveApp(isPass ? tab.appUrl : null);
  if (!tab.appUrl) setDeliveryPreview(isPass ? tab.preview || null : null);
  setGithubRepo(tab.githubUrl || null);
  const isRunning = Boolean(tab.runId) && !['PASS', 'FAIL', 'ERROR'].includes(tab.status);
  const engine = tab.engineLabel || selectedBackendLabel();
  resultCard.classList.toggle('is-running', isRunning);
  workingState.hidden = !isRunning;
  resultStatus.textContent = tab.status || 'QUEUED';
  resultMeta.textContent = isRunning
    ? `${engine} · 真实 Worker 正在处理 · 进度每 3 秒刷新`
    : tab.status === 'PASS'
      ? `${engine} · 已交付运行网页、浏览器验收与 GitHub 链接`
      : '截图已就绪，点击生成以创建真实 Worker run';
  taskState.textContent = isRunning ? 'CODEX WORKER · RUNNING' : tab.status === 'PASS' ? 'DELIVERY · PASS' : 'SCREENSHOT ATTACHED';
  generateBtn.disabled = isRunning;
  generateBtn.innerHTML = isRunning ? 'Worker 生成中 <span>…</span>' : `${tab.runId ? '重新生成' : '生成 MVP'} <span>↗</span>`;
  renderSourceTabs();
}

function selectSourceTab(id) {
  const tab = sourceTabs.find(item => item.id === id);
  if (!tab) return;
  selectedSource = tab;
  activeRunId = tab.runId || null;
  if (showMode) history.replaceState({}, '', activeRunId ? `/stage?run=${encodeURIComponent(activeRunId)}` : '/stage');
  clearInterval(pollTimer);
  renderSelectedSource();
  if (showMode && activeRunId && !['PASS', 'FAIL', 'ERROR'].includes(tab.status)) {
    loadRun();
    pollTimer = setInterval(loadRun, 3000);
  }
}

function addSourceTab({ file, source, name, app, runId = null, status = 'QUEUED', preview = null, appUrl = null, githubUrl = null }) {
  const tab = {
    id: runId || `screenshot-${Date.now()}-${++sourceTabCounter}`,
    file,
    source,
    name,
    app,
    runId,
    status,
    preview,
    appUrl,
    githubUrl,
  };
  sourceTabs.push(tab);
  return tab;
}

function resetDemoShell() {
  wholeDemoOverlay.hidden = true;
  $('.screenshot-app-shell').classList.remove('is-demo-generating');
  demoBrandName.textContent = 'SnapForge';
  demoBrandType.textContent = 'SCREENSHOT-TO-APP';
  $('#runtimeTag').textContent = 'LOCAL DEMO';
}

function startDemoShell(idea) {
  const name = idea || '截图生成 App';
  wholeDemoOverlay.hidden = false;
  $('.screenshot-app-shell').classList.add('is-demo-generating');
  demoBrandName.textContent = name;
  demoBrandType.textContent = 'IDEA-TO-MVP / DEMO PIPELINE';
  $('#runtimeTag').textContent = 'SIMULATING';
  overlayIdea.textContent = name;
  overlayTitle.textContent = '正在等待 MVP Worker 启动…';
  overlayStep.textContent = 'CCCC TEAM / 已接收 Idea 契约，正在分配构建任务';
}

$('#screenshotUpload').addEventListener('change', event => {
  const [file] = event.target.files;
  if (!file) return;
  const localUrl = URL.createObjectURL(file);
  const tab = addSourceTab({
    file,
    source: localUrl,
    name: file.name,
    app: `ScreenshotMVP-${String(sourceTabs.length + 1).padStart(2, '0')}`,
  });
  selectSourceTab(tab.id);
  event.target.value = '';
  toast(showMode ? '截图已回显，并新建独立工作页签。点击“生成 MVP”开始真实流水线。' : '截图已添加到演示任务；尚未上传至投递台');
});

function renderPhase(events, runStatus) {
  const phases = ['visual', 'scaffold', 'browser', 'delivery'];
  const latest = events.at(-1);
  const activeIndex = latest ? Math.max(0, phases.indexOf(latest.phase)) : 0;
  $$('#phaseProgress [data-phase]').forEach((node, index) => {
    node.classList.toggle('done', index < activeIndex || (index === activeIndex && latest?.status === 'PASS'));
    node.classList.toggle('active', index === activeIndex && runStatus !== 'PASS');
  });
  $('#runStageStatus').textContent = runStatus === 'PASS' ? 'RUNNING → PASS' : latest ? `${String(latest.phase).toUpperCase()} · ${latest.status}` : 'CONTRACT READY';
}

function renderTeamSummary(summary = {}, run = {}) {
  const cli = summary.cli || {};
  const idea = summary.idea || {};
  const foreman = summary.foreman || {};
  const cliCard = $('[data-summary="cli"]');
  const ideaCard = $('[data-summary="idea"]');
  const foremanCard = $('[data-summary="foreman"]');
  if (cli.records) {
    $('b', cliCard).textContent = `${cli.records} 条持久目录 · ${cli.selected_capabilities} 项入选`;
    $('small', cliCard).textContent = `CLI Agent 后台维护 · 本轮直接读取 · ${cli.validation || 'validate PASS'}`;
  }
  if (idea.options) {
    $('b', ideaCard).textContent = `${idea.options} 个方向 · ${idea.recommended || '已推荐'}`;
    const scores = idea.scores || {};
    $('small', ideaCard).textContent = Object.keys(scores).length
      ? `视觉 ${scores.visual_expression || '—'} · 通用 ${scores.generality || '—'} · 痛点 ${scores.pain_point || '—'} · 创新 ${scores.innovation || '—'}`
      : '视觉 · 通用 · 痛点 · 创新';
  }
  if (foreman.idea_id) {
    $('b', foremanCard).textContent = `${foreman.idea_id} · ${foreman.status || 'FROZEN'}`;
    $('small', foremanCard).textContent = `${foreman.contract || 'MVP contract'} → mvp-worker`;
  }
  const latestPhase = (run.events || []).at(-1)?.phase;
  const workerDone = run.status === 'PASS' || ['browser', 'delivery'].includes(latestPhase);
  const qaDone = run.status === 'PASS';
  $$('.team-roster .agent').forEach(node => {
    const role = node.dataset.agent;
    const done = role === 'foreman' ? Boolean(foreman.idea_id)
      : role === 'cli' ? Boolean(cli.records)
      : role === 'idea' ? Boolean(idea.options)
      : role === 'worker' ? workerDone
      : qaDone;
    const active = run.status !== 'PASS' && ((role === 'worker' && ['visual', 'scaffold', 'delivery'].includes(latestPhase)) || (role === 'qa' && latestPhase === 'browser'));
    node.classList.toggle('done', done);
    node.classList.toggle('active', active);
  });
}

function renderEvents(events, ccccEvents = [], teamEvents = []) {
  const stream = $('#logStream');
  stream.replaceChildren();
  const roleByPhase = { visual: 'WORKER', scaffold: 'WORKER', browser: 'QA', delivery: 'WORKER' };
  const combined = [
    ...teamEvents.map(event => ({ ...event, source: 'team' })),
    ...events.map(event => ({ ...event, actor: roleByPhase[event.phase] || 'WORKER', source: 'worker' })),
  ];
  if (!combined.length) {
    ccccEvents.forEach(event => combined.push({ ...event, actor: event.actor || 'CCCC', message: `${event.phase} · ${event.status} · ${event.engine}`, source: 'cccc' }));
  }
  if (!combined.length) appendAgentEvent('FOREMAN', '已读取持久能力库，正在派发 Idea Agent。', '', 'WAIT');
  combined.sort((a, b) => String(a.timestamp || '').localeCompare(String(b.timestamp || ''))).forEach(event => {
    const status = String(event.status || '');
    const kind = ['PASS', '通过', 'FROZEN'].includes(status) ? 'success' : ['FAIL', '失败'].includes(status) ? 'failed' : '';
    appendAgentEvent(event.actor || 'CCCC', event.message || `${event.phase || '阶段'} · ${status}`, kind, timeLabel(event.timestamp));
  });
  stream.scrollTop = stream.scrollHeight;
  $('#eventCount').textContent = `5 AGENTS · ${combined.length} EVENTS`;
}

function renderRun(payload) {
  latestRunPayload = payload;
  const { run, runtime, actor, backend } = payload;
  const execution = run.execution || {};
  const activeEngine = execution.label || backend?.label || '未记录执行引擎';
  const usedFallback = Boolean(execution.fallback);
  setRuntime(runtime, actor, backend);
  const app = run.app || {};
  const isPass = run.status === 'PASS';
  const isTerminal = ['PASS', 'FAIL', 'ERROR'].includes(run.status);
  const isRunning = !isTerminal && Boolean(run.dispatched);
  const hasLiveApp = isPass && Boolean(run.app_url);
  const latestPhase = (run.events || []).at(-1)?.phase || 'visual';
  let runTab = sourceTabByRunId(run.run_id);
  if (!runTab) {
    runTab = addSourceTab({
      source: run.source || '',
      name: `${app.name || '授权截图'} / ${run.run_id}`,
      app: app.name || 'ScreenshotMVP',
      runId: run.run_id,
      status: run.status,
      preview: run.preview || null,
      appUrl: run.app_url || null,
      githubUrl: run.github_url || null,
    });
  }
  Object.assign(runTab, {
    source: runTab.source || run.source || '',
    app: app.name || runTab.app || 'ScreenshotMVP',
    status: run.status,
    preview: run.preview || runTab.preview || null,
    appUrl: run.app_url || runTab.appUrl || null,
    githubUrl: run.github_url || runTab.githubUrl || null,
    engineLabel: activeEngine,
  });
  if (!selectedSource) selectedSource = runTab;
  renderSourceTabs();
  if (selectedSource.id !== runTab.id) return;
  $('#signalRunId').textContent = run.run_id;
  $('#deliveryRunId').textContent = run.run_id;
  $('#signalStatus').textContent = run.status;
  $('#signalDate').textContent = `本次运行 / ${timeLabel(run.created_at)}`;
  $('#deliveryStatus').textContent = run.status;
  $('#deliveryFiles').textContent = run.preview ? 'preview.png · acceptance-report.json · worker-delivery.json' : '正在等待 Worker 交付证据';
  sourceName.textContent = runTab.name;
  outputName.textContent = runTab.app;
  if (runTab.source) {
    sourcePreview.src = asset(runTab.source);
    sourcePreview.hidden = false;
    sourceEmpty.hidden = true;
  }
  resultPreview.alt = `${app.name || 'MVP'} 的真实 Worker 预览`;
  setLiveApp(hasLiveApp ? runTab.appUrl : null);
  if (!hasLiveApp) setDeliveryPreview(isPass ? runTab.preview || null : null);
  setGithubRepo(runTab.githubUrl || null);
  resultCard.classList.toggle('is-running', isRunning);
  workingState.hidden = !isRunning;
  if (isRunning) {
    const phaseCopy = {
      visual: ['正在理解截图', '视觉理解 · 识别布局、颜色与交互入口'],
      scaffold: ['正在生成 App', '前端构建 · 正在写入 HTML、CSS 与交互'],
      browser: ['正在浏览器验收', '自动检查布局、筛选和主操作'],
      delivery: ['正在封装交付', '正在准备预览图、验收报告与源码'],
    }[latestPhase] || ['正在生成 App', 'Worker 正在处理本次契约'];
    $('.simulation-tag').textContent = `${activeEngine} · ${String(latestPhase).toUpperCase()}`;
    $('#generationTitle').textContent = phaseCopy[0];
    $('#generationStep').textContent = phaseCopy[1];
  }
  resultStatus.textContent = run.status;
  resultMeta.textContent = isPass
    ? `${activeEngine}${usedFallback ? '（本地离线自动兜底）' : ''} · 真实产物 · preview.png · 验收报告`
    : run.dispatched
      ? `${activeEngine}${usedFallback ? '（本地离线自动兜底）' : ''} · 真实 Worker 正在处理 · 进度每 3 秒刷新`
      : '契约已就绪，尚未派发';
  taskState.textContent = isPass
    ? (usedFallback ? 'CODEX FALLBACK · PASS' : 'DELIVERY · PASS')
    : run.dispatched
      ? (usedFallback ? 'CODEX FALLBACK · RUNNING' : 'CCCC WORKER · RUNNING')
      : 'CONTRACT · READY';
  generateBtn.disabled = isRunning;
  generateBtn.innerHTML = isRunning ? 'Worker 生成中 <span>…</span>' : '重新生成 <span>↗</span>';
  renderTeamSummary(run.team_summary || {}, run);
  renderPhase(run.events || [], run.status);
  renderEvents(run.events || [], stageSnapshot.events || [], run.team_summary?.events || []);
}

function renderCcccStage(stage, runtime, actor, backend) {
  stageSnapshot = stage || { events: [] };
  setRuntime(runtime, actor, backend);
  if (stage?.title) $('#runStageStatus').textContent = `${stage.title} · LIVE`;
  if (latestRunPayload?.run?.run_id === activeRunId) {
    renderEvents(latestRunPayload.run.events || [], stageSnapshot.events || [], latestRunPayload.run.team_summary?.events || []);
  } else if (stageSnapshot.events?.length) {
    renderEvents([], stageSnapshot.events);
  }
}

async function loadRun() {
  if (!showMode || !activeRunId) return;
  const requestedRunId = activeRunId;
  try {
    const response = await fetch(`/api/runs/${encodeURIComponent(requestedRunId)}`, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '无法读取该试跑');
    // A request for the prior run may finish after the operator has just
    // submitted a new screenshot. Never let that stale response overwrite
    // the new left preview or its active generation animation.
    if (requestedRunId !== activeRunId) return;
    renderRun(data);
  } catch (error) {
    clearInterval(pollTimer);
    taskState.textContent = 'LOCAL DEMO MODE';
    toast(error.message || '运行台暂时无法连接');
  }
}

async function loadStage() {
  if (!stageMode) return;
  try {
    const suffix = activeRunId ? `?run=${encodeURIComponent(activeRunId)}` : '';
    const response = await fetch(`/api/stage${suffix}`, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '无法读取 CCCC 舞台状态');
    renderCcccStage(data.stage, data.runtime, data.actor, data.backend);
  } catch (error) {
    $('#eventCount').textContent = 'CCCC 状态暂不可用';
  }
}

async function createRealRun() {
  if (!selectedSource) {
    toast('请先上传一张授权截图。');
    return;
  }
  generateBtn.disabled = true;
  const requestedBackend = selectedBackend();
  const requestedEngine = selectedBackendLabel();
  resultCard.classList.add('is-running');
  workingState.hidden = false;
  $('.simulation-tag').textContent = `${requestedEngine} · 正在理解左侧截图`;
  $('#generationTitle').textContent = '正在从截图提取布局与交互意图…';
  $('#generationStep').textContent = 'MVP-WORKER / 视觉理解 → 前端脚手架 → 浏览器验收';
  taskState.textContent = 'FOREMAN · CREATING CONTRACT';
  resultStatus.textContent = 'QUEUED';
  resultMeta.textContent = `${requestedEngine} · 保存截图 → 创建契约 → 派发 Worker`;
  try {
    let screenshot = selectedSource.file;
    if (!screenshot) {
      const response = await fetch(asset(selectedSource.source));
      if (!response.ok) throw new Error('演示截图未能读取');
      const blob = await response.blob();
      screenshot = new File([blob], `${selectedSource.app}.jpg`, { type: blob.type || 'image/jpeg' });
    }
    const form = new FormData();
    form.set('screenshot', screenshot);
    form.set('app_name', selectedSource.app);
    form.set('kind', 'mobile app');
    form.set('backend', requestedBackend);
    form.set('dispatch', 'true');
    if (activeIncubationRunId) form.set('incubation_run_id', activeIncubationRunId);
    const response = await fetch('/api/intake', { method: 'POST', body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '投递失败');
    activeRunId = data.run_id;
    Object.assign(selectedSource, {
      runId: data.run_id,
      status: 'RUNNING',
      preview: null,
      appUrl: null,
      githubUrl: null,
      engineLabel: requestedEngine,
    });
    history.replaceState({}, '', data.stage_url || `/stage?run=${encodeURIComponent(activeRunId)}`);
    renderSelectedSource();
    toast(`已创建 ${activeRunId}，左侧现在展示真实 Worker 日志。`);
    await loadRun();
    clearInterval(pollTimer);
    pollTimer = setInterval(loadRun, 3000);
  } catch (error) {
    resultCard.classList.remove('is-running');
    workingState.hidden = true;
    $('.simulation-tag').textContent = '真实 Worker · 未能启动';
    resultStatus.textContent = 'ERROR';
    resultMeta.textContent = '请到 Worker 投递台确认服务与 CCCC 状态';
    taskState.textContent = 'SUBMIT FAILED';
    toast(error.message || '投递失败');
  } finally {
    generateBtn.disabled = Boolean(selectedSource?.runId && !['PASS', 'FAIL', 'ERROR'].includes(selectedSource.status));
  }
}

function simulateBuild() {
  const instruction = $('#buildPrompt').value.trim() || '按截图的布局与交互意图生成可运行的前端 MVP。';
  const selectedIdea = $('.idea-card.selected h3')?.textContent || '截图生成 App';
  const generationTitle = $('#generationTitle');
  const generationStep = $('#generationStep');
  generateBtn.disabled = true;
  startDemoShell(selectedIdea);
  resultCard.classList.add('is-running');
  workingState.hidden = false;
  taskState.textContent = 'DEMO · WAITING FOR MVP-WORKER';
  resultStatus.textContent = 'SIMULATING';
  resultMeta.textContent = `演示模拟 · ${selectedIdea} → SnapForge 案例`;
  generationTitle.textContent = '正在等待 MVP Worker 启动…';
  generationStep.textContent = 'CCCC TEAM / 已接收 Idea 契约，正在分配构建任务';
  appendAgentEvent('FOREMAN', `演示模式：接收「${selectedIdea}」，等待 MVP-WORKER 启动。`);
  setTimeout(() => {
    taskState.textContent = 'DEMO · MVP-WORKER STARTING';
    generationTitle.textContent = 'MVP Worker 已接手，正在准备构建…';
    generationStep.textContent = 'MVP-WORKER / 初始化运行环境与浏览器会话';
    overlayTitle.textContent = 'MVP Worker 已接手，正在准备构建…';
    overlayStep.textContent = 'MVP-WORKER / 初始化运行环境与浏览器会话';
    appendAgentEvent('MVP-WORKER', '演示模式：Worker 已接手，正在准备构建环境。');
  }, 900);
  setTimeout(() => {
    taskState.textContent = 'DEMO · SNAPFORGE HANDOFF';
    generationTitle.textContent = '正在载入已准备的展示案例…';
    generationStep.textContent = 'DEMO ROUTER / SnapForge prepared case';
    overlayTitle.textContent = '正在载入已准备的展示案例…';
    overlayStep.textContent = 'DEMO ROUTER / SnapForge prepared case';
    appendAgentEvent('QA', '演示模式：准备切换至 SnapForge 展示案例。');
  }, 1900);
  setTimeout(() => {
    resultCard.classList.remove('is-running');
    workingState.hidden = true;
    resetDemoShell();
    generateBtn.disabled = false;
    taskState.textContent = 'DEMO · SNAPFORGE READY';
    outputName.textContent = selectedSource.custom ? 'SnapForge Demo' : selectedSource.app;
    resultPreview.src = asset(selectedSource.output);
    setLiveApp(demoAppUrl(selectedSource.runId));
    resultStatus.textContent = 'PASS';
    resultMeta.textContent = '演示完成 · 已切换至 SnapForge 准备案例';
    appendAgentEvent('QA', `演示模拟结束，展示已准备的 SnapForge 案例：${instruction.slice(0, 22)}${instruction.length > 22 ? '…' : ''}`, 'success');
    toast('演示模拟完成，已展示 SnapForge 准备案例。');
  }, 2850);
}

generateBtn.addEventListener('click', () => showMode ? createRealRun() : simulateBuild());

typeCommand();
loadCliCatalog();
renderEmptySource();
applyStageSplit();
loadIncubation();
window.incubationTimer = setInterval(loadIncubation, 5000);
if (showMode && activeRunId) {
  loadRun();
  loadStage();
  pollTimer = setInterval(loadRun, 3000);
  stageTimer = setInterval(loadStage, 3000);
} else if (showMode) {
  loadStage();
  stageTimer = setInterval(loadStage, 3000);
}
