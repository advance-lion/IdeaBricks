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

$$('.chip').forEach(chip => chip.addEventListener('click', () => chip.classList.toggle('selected')));

$('#cliToggle').addEventListener('click', () => {
  const extras = $$('.cli-extra');
  const expanded = $('#cliToggle').getAttribute('aria-expanded') === 'true';
  extras.forEach(item => item.hidden = expanded);
  $('#cliToggle').setAttribute('aria-expanded', String(!expanded));
  $('#cliToggle').textContent = expanded ? '展开清单 +' : '收起清单 −';
  $('#cliCount').textContent = expanded ? '已展示 6 / 12 个 CLI' : '已展示 12 / 12 个 CLI';
  toast(expanded ? '已收起扩展 CLI 清单' : '已展开完整 CLI 能力清单');
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
  $('#taskState').textContent = card.dataset.idea === 'screenshot-app' ? 'READY TO FORGE' : 'DEMO MODE';
  toast(card.dataset.idea === 'screenshot-app' ? '已切换到截图生成 App 的演示操作台' : `已选中「${name}」；当前展示仍使用截图生成 Worker 链路`);
  $('#mvp').scrollIntoView({ behavior: 'smooth', block: 'start' });
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
  const form = latest.cli_form || {};
  const shortlist = latest.shortlist || {};
  const contract = latest.mvp_contract || {};
  const capabilities = firstArray(form.capabilities, form.items, form.tools);
  const ideas = firstArray(shortlist.ideas, shortlist.ranked_ideas, shortlist.ranked_options, shortlist.results, shortlist.candidates);
  const statusMap = {
    FOREMAN_QUEUED: 'Foreman 已接收',
    WAITING_FOR_IDEA_AGENT: '等待 Idea Agent',
    IDEAS_RANKED: 'A2 已完成排序',
    MVP_CONTRACT_READY: 'MVP 契约已冻结',
  };
  state.textContent = statusMap[latest.status] || latest.status;
  state.classList.toggle('wait', latest.status === 'FOREMAN_QUEUED' || latest.status === 'WAITING_FOR_IDEA_AGENT');
  if (latest.brief) $('#briefInput').value = latest.brief;
  $('#ideaMatch').textContent = capabilities.length ? `${capabilities.length} 项可用能力` : '等待 CLI 表单';
  $('#ideaCapabilities').innerHTML = capabilities.length
    ? capabilities.slice(0, 4).map(item => `<li><i>✓</i> ${escapeHtml(item.name || item.capability || item.id)}</li>`).join('')
    : '<li><i>·</i> 等待 Foreman 交接能力表单</li>';
  $('#ideaResultsTitle').textContent = ideas.length ? `A2 排序出的 ${ideas.length} 个方向` : 'Foreman → Idea Agent 正在交接';
  $('#ideaEvidence').textContent = form.demo_only ? 'CLI 表单：集成测试模拟' : 'CLI 表单：正式输入';
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
    return `<article class="idea-card ${selected ? 'selected' : ''}" data-idea="${escapeHtml(id)}"><div class="idea-no">${String(index + 1).padStart(2, '0')}</div><div class="idea-main"><div class="card-title"><h3>${escapeHtml(title)}</h3><span>${selected ? '已冻结' : 'A2 已评估'}</span></div><p>${escapeHtml(description)}</p><div class="tag-row">${tags.map(tag => `<i>${escapeHtml(typeof tag === 'string' ? tag : tag.name || tag.id)}</i>`).join('')}</div></div><div class="score"><b>${score || '—'}</b><span>综合分</span></div><button class="select-idea">${selected ? '查看 MVP' : '选择方向'} <span>→</span></button></article>`;
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
  button.disabled = true;
  button.innerHTML = 'Foreman 正在交接… <span>···</span>';
  try {
    const response = await fetch('/api/incubation/test', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brief: $('#briefInput').value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '无法创建创意测试');
    renderIncubation({ team: { actors: [] }, latest: data.latest });
    toast(`${data.latest.run_id} 已交给 Foreman；A2 结果会自动回填到这里。`);
    clearInterval(window.incubationTimer);
    window.incubationTimer = setInterval(loadIncubation, 3500);
  } catch (error) {
    toast(error.message || '创意测试未能启动');
  } finally {
    button.disabled = false;
    button.innerHTML = '用 Team 重新挖掘 <span>↗</span>';
  }
}

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
const mvpStage = $('#mvpStage');
const stageDivider = $('#stageDivider');
let selectedSource = {
  source: 'inputs/screenshot-to-app-recording-001/fastbite-reference.jpg',
  name: 'KFC 点餐截图',
  app: 'FastBite',
  output: 'runs/fastbite-kfc-001/artifacts/preview.png',
  runId: 'fastbite-kfc-001',
  custom: false,
};

function demoAppUrl(runId) {
  if (!runId) return null;
  return showMode ? `/apps/${encodeURIComponent(runId)}/index.html` : `runs/${runId}/app/index.html`;
}

function setLiveApp(url) {
  if (!url) {
    resultFrame.removeAttribute('src');
    resultFrame.hidden = true;
    openApp.hidden = true;
    resultPreview.hidden = false;
    return;
  }
  resultFrame.src = url;
  resultFrame.hidden = false;
  openApp.href = url;
  openApp.hidden = false;
  resultPreview.hidden = true;
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

function setSource(button) {
  $$('.source-chip').forEach(chip => chip.classList.remove('selected'));
  button.classList.add('selected');
  selectedSource = {
    source: button.dataset.source,
    name: button.dataset.name,
    app: button.dataset.app,
    output: button.dataset.output,
    runId: button.dataset.runId,
    custom: false,
  };
  sourcePreview.src = asset(selectedSource.source);
  sourcePreview.alt = `待解析的${selectedSource.name}`;
  sourceName.textContent = selectedSource.name;
  outputName.textContent = selectedSource.app;
  resultPreview.src = asset(selectedSource.output);
  resultPreview.alt = `生成的${selectedSource.app} MVP 预览`;
  setLiveApp(demoAppUrl(selectedSource.runId));
  resultStatus.textContent = 'READY';
  resultMeta.textContent = showMode ? '点击生成，创建真实 Worker run' : '点击生成以启动演示流程';
  taskState.textContent = 'READY TO FORGE';
}

$$('.source-chip').forEach(button => button.addEventListener('click', () => setSource(button)));

$('#screenshotUpload').addEventListener('change', event => {
  const [file] = event.target.files;
  if (!file) return;
  const localUrl = URL.createObjectURL(file);
  $$('.source-chip').forEach(chip => chip.classList.remove('selected'));
  selectedSource = { source: localUrl, file, name: file.name, app: 'SparkMVP', output: selectedSource.output, runId: null, custom: true };
  sourcePreview.src = localUrl;
  sourcePreview.alt = `本地上传的${file.name}`;
  sourceName.textContent = file.name;
  outputName.textContent = '等待 Worker 交付';
  setLiveApp(null);
  resultStatus.textContent = 'QUEUED';
  resultMeta.textContent = showMode ? '点击生成后会投递给真实 Worker' : '截图已在当前浏览器本地预览';
  taskState.textContent = 'SCREENSHOT ATTACHED';
  toast(showMode ? '截图已就绪，下一步会创建独立契约并派发。' : '截图已添加到演示任务；尚未上传至投递台');
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

function renderEvents(events, ccccEvents = []) {
  const stream = $('#logStream');
  stream.replaceChildren();
  const roleByPhase = { visual: 'VISION', scaffold: 'MVP-WORKER', browser: 'QA', delivery: 'DELIVERY' };
  if (!events.length) appendAgentEvent('FOREMAN', '契约已创建，等待 mvp-worker 写入第一条真实进度。', '', 'WAIT');
  events.forEach(event => {
    const agent = roleByPhase[event.phase] || 'MVP-WORKER';
    const kind = event.status === 'PASS' ? 'success' : event.status === 'FAIL' ? 'failed' : '';
    appendAgentEvent(agent, event.message || `${event.phase} ${event.status}`, kind, timeLabel(event.timestamp));
  });
  ccccEvents.forEach(event => {
    const kind = event.status === '通过' ? 'success' : event.status === '失败' ? 'failed' : '';
    appendAgentEvent('CCCC', `${event.phase} · ${event.status} · ${event.engine}`, kind, timeLabel(event.timestamp));
  });
  stream.scrollTop = stream.scrollHeight;
  $('#eventCount').textContent = `${events.length} WORKER + ${ccccEvents.length} CCCC`;
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
  const isRunning = !isPass && Boolean(run.dispatched);
  $('#signalRunId').textContent = run.run_id;
  $('#deliveryRunId').textContent = run.run_id;
  $('#signalStatus').textContent = run.status;
  $('#signalDate').textContent = `本次运行 / ${timeLabel(run.created_at)}`;
  $('#deliveryStatus').textContent = run.status;
  $('#deliveryFiles').textContent = run.preview ? 'preview.png · acceptance-report.json · worker-delivery.json' : '正在等待 Worker 交付证据';
  sourceName.textContent = `${app.name || 'SparkMVP'} / 授权截图`;
  outputName.textContent = app.name || '等待 Worker 交付';
  if (run.source) sourcePreview.src = run.source;
  if (run.preview) resultPreview.src = run.preview;
  resultPreview.alt = `${app.name || 'MVP'} 的真实 Worker 预览`;
  setLiveApp(run.app_url || null);
  resultCard.classList.toggle('is-running', isRunning);
  workingState.hidden = !isRunning;
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
  renderPhase(run.events || [], run.status);
  renderEvents(run.events || [], stageSnapshot.events || []);
}

function renderCcccStage(stage, runtime, actor, backend) {
  stageSnapshot = stage || { events: [] };
  setRuntime(runtime, actor, backend);
  if (stage?.title) $('#runStageStatus').textContent = `${stage.title} · LIVE`;
  if (latestRunPayload?.run?.run_id === activeRunId) {
    renderEvents(latestRunPayload.run.events || [], stageSnapshot.events || []);
  } else if (stageSnapshot.events?.length) {
    renderEvents([], stageSnapshot.events);
  }
}

async function loadRun() {
  if (!showMode || !activeRunId) return;
  try {
    const response = await fetch(`/api/runs/${encodeURIComponent(activeRunId)}`, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '无法读取该试跑');
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
    if (!activeRunId && data.stage?.latest_run_id) {
      activeRunId = data.stage.latest_run_id;
      history.replaceState({}, '', `/stage?run=${encodeURIComponent(activeRunId)}`);
      await loadRun();
    }
    renderCcccStage(data.stage, data.runtime, data.actor, data.backend);
  } catch (error) {
    $('#eventCount').textContent = 'CCCC 状态暂不可用';
  }
}

async function createRealRun() {
  generateBtn.disabled = true;
  resultCard.classList.add('is-running');
  workingState.hidden = false;
  taskState.textContent = 'FOREMAN · CREATING CONTRACT';
  resultStatus.textContent = 'QUEUED';
  resultMeta.textContent = '保存截图 → 创建契约 → 派发 Worker';
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
    form.set('dispatch', 'true');
    const response = await fetch('/api/intake', { method: 'POST', body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '投递失败');
    activeRunId = data.run_id;
    history.replaceState({}, '', data.stage_url || `/stage?run=${encodeURIComponent(activeRunId)}`);
    toast(`已创建 ${activeRunId}，左侧现在展示真实 Worker 日志。`);
    await loadRun();
    clearInterval(pollTimer);
    pollTimer = setInterval(loadRun, 3000);
  } catch (error) {
    resultCard.classList.remove('is-running');
    workingState.hidden = true;
    resultStatus.textContent = 'ERROR';
    resultMeta.textContent = '请到 Worker 投递台确认服务与 CCCC 状态';
    taskState.textContent = 'SUBMIT FAILED';
    toast(error.message || '投递失败');
  } finally {
    generateBtn.disabled = false;
  }
}

function simulateBuild() {
  const instruction = $('#buildPrompt').value.trim() || '按截图的布局与交互意图生成可运行的前端 MVP。';
  generateBtn.disabled = true;
  resultCard.classList.add('is-running');
  workingState.hidden = false;
  taskState.textContent = 'FOREMAN · ANALYSING';
  resultStatus.textContent = 'RUNNING';
  resultMeta.textContent = 'vision → scaffold → browser';
  appendAgentEvent('FOREMAN', `接收截图「${selectedSource.name}」与生成指令`);
  setTimeout(() => { taskState.textContent = 'MVP-WORKER · BUILDING'; appendAgentEvent('MVP-WORKER', '正在提取布局结构并生成静态前端…'); }, 650);
  setTimeout(() => { taskState.textContent = 'QA · CHECKING'; appendAgentEvent('QA', '正在执行浏览器验收与交付封装…'); }, 1350);
  setTimeout(() => {
    resultCard.classList.remove('is-running');
    workingState.hidden = true;
    generateBtn.disabled = false;
    taskState.textContent = 'DEMO RUN · PASS';
    outputName.textContent = selectedSource.custom ? 'Demo MVP 预览' : selectedSource.app;
    resultPreview.src = asset(selectedSource.output);
    setLiveApp(demoAppUrl(selectedSource.runId));
    resultStatus.textContent = 'PASS';
    resultMeta.textContent = 'preview.png · acceptance-report.json';
    appendAgentEvent('QA', `演示流程完成：${instruction.slice(0, 24)}${instruction.length > 24 ? '…' : ''}`, 'success');
    toast('演示生成完成；投递台服务启动后会切换为真实交付物。');
  }, 2150);
}

generateBtn.addEventListener('click', () => showMode ? createRealRun() : simulateBuild());

typeCommand();
setSource($('.source-chip.selected'));
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
