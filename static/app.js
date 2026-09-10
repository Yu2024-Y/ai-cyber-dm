// AI 赛博 DM：战役大厅 + 角色选择 + 多人跑团（SSE 流式/场景卡/剧情树/TTS）
const $ = (id) => document.getElementById(id);

const DEFAULT_INTRO =
  '夜色把这座城吞进霓虹里，雨丝混着冷却液的气味落在你的肩头。一条新的委托正等在暗处——你们的队伍已经集结，第一步，往哪走？';

// ---------------- 视图与全局状态 ----------------
const views = { lobby: $('view-lobby'), roles: $('view-roles'), game: $('view-game') };
let G = null;                 // {id, name}
let me = null;                // {key, name, color}
let myNonces = new Set();     // 本页会话已发送的 nonce（去重）
let lastMsgId = 0;
let pollTimer = null;
let scenePollGuard = false;
let activeSceneTask = null;
let speakToken = 0;           // 新语音会打断旧的
let currentAudio = null;      // 当前正在播放的音频（打断用）

function showView(name) {
  Object.entries(views).forEach(([k, el]) => { el.hidden = k !== name; });
}

function toast(text) {
  const t = $('toast');
  t.textContent = text;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2200);
}

function makeNonce() {
  return (crypto.randomUUID ? crypto.randomUUID() : Date.now() + '-' + Math.random().toString(36).slice(2));
}

// DM 富文本：HTML 转义后把 **关键信息** 渲染成高亮（其余原样显示）
function escHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function renderRich(text) {
  const esc = escHtml(text);
  const parts = esc.split('**');
  if (parts.length < 3) return esc; // 没有成对星号就原样
  let out = '';
  for (let i = 0; i < parts.length; i++) {
    if (i % 2 === 1 && parts[i]) out += '<b class="hl">' + parts[i] + '</b>';
    else out += parts[i];
  }
  return out;
}

function identityKey(gid) { return 'aidm_role_' + gid; }

// ---------------- API ----------------
async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    let detail = '请求失败';
    try { detail = (await res.json()).detail || detail; } catch (e) { /* ignore */ }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? null : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = '请求失败';
    try { detail = (await res.json()).detail || detail; } catch (e) { /* ignore */ }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// ---------------- 大厅 ----------------
function fmtTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  } catch (e) { return ''; }
}

async function refreshLobby() {
  const box = $('lobby-list');
  box.innerHTML = '<div class="empty">加载中…</div>';
  try {
    const data = await getJson('/api/games');
    if (!data.games.length) {
      box.innerHTML = '<div class="empty">还没有战役，输入名称开始第一局吧。</div>';
      return;
    }
    box.innerHTML = '';
    for (const g of data.games) {
      const card = document.createElement('div');
      card.className = 'game-card';
      const info = document.createElement('div');
      const name = document.createElement('div');
      name.className = 'gn';
      name.textContent = '🎲 ' + g.name;
      const meta = document.createElement('div');
      meta.className = 'meta';
      meta.textContent = `👥 ${g.player_count} 人 · 💬 ${g.message_count} 条 · ${fmtTime(g.created_at)}`;
      info.appendChild(name);
      info.appendChild(meta);
      const btn = document.createElement('button');
      btn.className = 'gbtn';
      btn.textContent = '进入';
      btn.addEventListener('click', () => openGame(g.id));
      card.appendChild(info);
      card.appendChild(btn);
      box.appendChild(card);
    }
  } catch (e) {
    box.innerHTML = '<div class="empty">加载失败：' + e.message + '</div>';
  }
}

async function openGame(gid) {
  try {
    const data = await getJson('/api/games/' + gid);
    G = { id: data.game.id, name: data.game.name };
    const saved = sessionStorage.getItem(identityKey(gid));
    if (saved) {
      try { me = JSON.parse(saved); } catch (e) { me = null; }
    }
    if (me) {
      enterGame();
    } else {
      showRoles();
    }
  } catch (e) {
    if (e.status === 404) {
      // 存档里的战役已不存在 → 清掉残留身份
      sessionStorage.removeItem(identityKey(gid));
      toast('该战役已不存在，请新建或选择其他战役');
    } else {
      toast('进入失败：' + e.message);
    }
  }
}

async function createGame() {
  const name = $('new-name').value.trim();
  if (!name) { toast('给战役起个名字吧'); return; }
  $('btn-new').disabled = true;
  try {
    const data = await postJson('/api/games', { name });
    $('new-name').value = '';
    await openGame(data.game.id);
    await refreshLobby();
  } catch (e) {
    toast('创建失败：' + e.message);
  } finally {
    $('btn-new').disabled = false;
  }
}

// ---------------- 选角色 ----------------
let pendingGameName = '';

async function showRoles() {
  if (!G) return;
  pendingGameName = G.name;
  $('role-game-name').textContent = '「' + G.name + '」';
  showView('roles');
  await renderRoleCards();
}

async function renderRoleCards() {
  const grid = $('role-cards');
  grid.innerHTML = '<div class="empty">加载角色中…</div>';
  let roles = [], taken = new Set();
  try {
    const [rd, pd] = await Promise.all([getJson('/api/roles'), getJson('/api/games/' + G.id + '/players')]);
    roles = rd.roles;
    taken = new Set(pd.players.map((p) => p.name));
  } catch (e) {
    grid.innerHTML = '<div class="empty">加载失败：' + e.message + '</div>';
    return;
  }
  grid.innerHTML = '';
  for (const r of roles) {
    const card = document.createElement('button');
    card.className = 'role-card' + (taken.has(r.name) ? ' taken' : '');
    card.disabled = taken.has(r.name);
    card.style.setProperty('--role', r.color);
    const top = document.createElement('div');
    top.className = 'rc-top';
    top.innerHTML = '';
    const emoji = document.createElement('span');
    emoji.className = 'emoji';
    emoji.textContent = r.emoji;
    const nm = document.createElement('span');
    nm.className = 'nm';
    nm.textContent = r.name;
    const cs = document.createElement('span');
    cs.className = 'cs';
    cs.textContent = r.callsign;
    top.append(emoji, nm, cs);
    const title = document.createElement('div');
    title.className = 'rc-title';
    title.textContent = r.title;
    const skills = document.createElement('div');
    skills.className = 'rc-skills';
    r.skills.forEach((s) => {
      const t = document.createElement('span');
      t.className = 'rc-skill';
      t.textContent = s;
      skills.appendChild(t);
    });
    const desc = document.createElement('div');
    desc.className = 'rc-desc';
    desc.textContent = r.desc;
    card.append(top, title, skills, desc);
    if (taken.has(r.name)) {
      const ft = document.createElement('div');
      ft.className = 'rc-foot rc-taken';
      ft.textContent = '✗ 已被其他玩家加入';
      card.appendChild(ft);
    } else {
      const ft = document.createElement('div');
      ft.className = 'rc-foot';
      ft.textContent = '选择此角色加入 →';
      card.appendChild(ft);
      card.addEventListener('click', () => joinRole(r.key));
    }
    grid.appendChild(card);
  }
}

async function joinRole(key) {
  try {
    const data = await postJson('/api/games/' + G.id + '/join', { role_key: key });
    me = { key: data.player.role_key, name: data.player.name, color: data.player.color };
    sessionStorage.setItem(identityKey(G.id), JSON.stringify(me));
    toast('以「' + me.name + '」加入战役');
    enterGame();
  } catch (e) {
    toast(e.message);
    renderRoleCards(); // 刷新占用状态
  }
}

// ---------------- 游戏内：消息渲染 ----------------
const PALETTE = {};

function stripAction(content) {
  // 存储格式为 "[名字的行动] 内容"；渲染时去掉前缀，名字用 who 标签展示
  return content.replace(/^\[[^\]]*\]\s*/, '');
}

function bubbleFor(m, streamed) {
  const isDM = m.role === 'assistant';
  const isMine = m.role === 'user' && me && m.player === me.name;
  const isDice = !isDM && (m.content || '').includes('🎲');
  const div = document.createElement('div');
  div.className = 'msg ' + (isDM ? 'dm' : 'user') + (isDice ? ' dice' : '') + (isMine ? '' : ' other');
  if (m.role === 'user') {
    const who = document.createElement('div');
    who.className = 'who';
    const color = (me && m.player === me.name ? me.color : m.color) || '#46e7ff';
    div.style.setProperty('--who', color);
    who.textContent = m.player ? '【' + m.player + '】' : '玩家';
    div.insertBefore(who, div.firstChild);
  }
  const body = document.createElement('div');
  body.className = 'dbody';
  if (isDM) {
    body.innerHTML = renderRich(m.content); // DM 支持 **关键词** 高亮
  } else {
    body.textContent = stripAction(m.content);
  }
  div.appendChild(body);
  return div;
}

function appendMsgEl(div) {
  $('chat').appendChild(div);
  $('chat').scrollTop = $('chat').scrollHeight;
}

function renderHistory(messages) {
  const chat = $('chat');
  chat.innerHTML = '';
  if (!messages.length) {
    const sys = document.createElement('div');
    sys.className = 'msg sys';
    sys.textContent = DEFAULT_INTRO;
    chat.appendChild(sys);
    return;
  }
  messages.forEach((m) => appendMsgEl(bubbleFor(m)));
}

function appendRemote(m) {
  // 轮询到的"别人"消息
  appendMsgEl(bubbleFor(m));
}

// ---------------- 多人轮询 ----------------
async function pollTick() {
  if (!G) return;
  try {
    const [md, pd] = await Promise.all([
      getJson('/api/games/' + G.id + '/messages?after_id=' + lastMsgId),
      getJson('/api/games/' + G.id + '/players'),
    ]);
    let newLast = lastMsgId;
    for (const m of md.messages) {
      if (m.id > newLast) newLast = m.id;
      if (m.nonce && myNonces.has(m.nonce)) continue; // 自己刚发/刚流式的，已上屏
      appendRemote(m);
    }
    lastMsgId = newLast;
    renderRoster(pd.players);
    refreshStoryTree();
  } catch (e) { /* 轮询失败忽略，下轮重试 */ }
}

function startPoll() {
  clearInterval(pollTimer);
  pollTimer = setInterval(pollTick, 2000);
}

function renderRoster(players) {
  const roster = $('roster');
  roster.innerHTML = '';
  // “我”固定显示在右上 me-chip，名单里不再重复
  if (me) {
    $('me-chip').innerHTML = '';
    const meDot = document.createElement('span');
    meDot.className = 'dot';
    meDot.style.background = me.color;
    meDot.style.color = me.color;
    $('me-chip').append(meDot, document.createTextNode(me.name));
  }
  players.forEach((p) => {
    if (me && p.name === me.name) return;
    const chip = document.createElement('span');
    chip.className = 'chip';
    const dot = document.createElement('span');
    dot.className = 'dot';
    dot.style.background = p.color;
    dot.style.color = p.color;
    chip.append(dot, document.createTextNode(p.name));
    roster.appendChild(chip);
  });
}

// ---------------- 语音：按句切块顺序播放 ----------------
function splitSpeech(text) {
  // 切成 ≤120 字、以句号/叹号/问号等自然断点结尾的分块
  const chunks = [];
  let buf = '';
  for (const ch of text) {
    buf += ch;
    if (/[。！？…\n]/.test(ch) && buf.length >= 24) {
      chunks.push(buf.trim());
      buf = '';
    } else if (buf.length >= 120) {
      chunks.push(buf.trim());
      buf = '';
    }
  }
  if (buf.trim()) chunks.push(buf.trim());
  return chunks;
}

async function speakText(text) {
  const token = ++speakToken;
  // 说话前立刻暂停上一段朗读，杜绝两段重叠
  if (currentAudio) {
    try { currentAudio.pause(); } catch (e) { /* ignore */ }
    currentAudio = null;
  }
  const keepRefs = [];
  const clean = text.replace(/\*\*/g, ''); // 语音不读星号，仅读文字
  for (const seg of splitSpeech(clean)) {
    if (token !== speakToken) return; // 已被新一轮语音打断
    try {
      const res = await fetch('/api/tts?text=' + encodeURIComponent(seg));
      if (!res.ok) continue;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      keepRefs.push(audio);
      currentAudio = audio;
      await new Promise((resolve) => {
        const done = () => {
          if (currentAudio === audio) currentAudio = null;
          resolve();
        };
        audio.onended = done;
        audio.onerror = done;
        audio.addEventListener('pause', done); // 被新朗读打断时立刻收尾退出
        audio.play().catch(done);
      });
    } catch (e) { /* 一段失败继续下一段 */ }
  }
}

// ---------------- 场景卡 ----------------
const STATUS_LABEL = { PENDING: '排队中', RUNNING: '绘制中', SUCCESS: '已完成', FAILED: '失败' };

function renderScene(snap) {
  if (!snap) return;
  $('scene-status').textContent = STATUS_LABEL[snap.status] || snap.status;
  const body = $('scene-body');
  if (snap.status === 'SUCCESS' && snap.image_url) {
    body.innerHTML = '<img src="' + snap.image_url + '" alt="场景图">';
  } else if (snap.status === 'FAILED') {
    const why = snap.error ? snap.error.slice(0, 40) : '重试耗尽';
    body.innerHTML = '<span>😵 场景生成失败 · 已降级占位图（' + why + '）</span>';
  } else {
    body.innerHTML = '<div class="skeleton"></div>';
  }
}

async function pollScene(taskId) {
  if (scenePollGuard) return;
  scenePollGuard = true;
  try {
    for (let i = 0; i < 40; i++) {
      if (activeSceneTask !== taskId) return; // 已被更新的任务取代
      await new Promise((r) => setTimeout(r, 1500));
      let snap;
      try { snap = await getJson('/api/games/' + G.id + '/scene/task/' + taskId); } catch (e) { continue; }
      renderScene(snap);
      if (snap.status === 'SUCCESS' || snap.status === 'FAILED') return;
    }
  } finally {
    scenePollGuard = false;
  }
}

async function triggerScene(force) {
  if (!G) return;
  try {
    const snap = await postJson('/api/games/' + G.id + '/scene?force=' + (force ? '1' : '0'));
    activeSceneTask = snap.task_id;
    renderScene(snap);
    if (snap.status === 'PENDING' || snap.status === 'RUNNING') pollScene(snap.task_id);
  } catch (e) {
    $('scene-status').textContent = '—';
  }
}

// ---------------- 剧情树 ----------------
function storyNode(node) {
  const li = document.createElement('li');
  li.className = 'tn-' + (node.kind || 'story');
  const label = document.createElement('span');
  label.className = 'tlabel';
  label.textContent = node.title || '';
  li.appendChild(label);
  if (node.children && node.children.length) {
    const ul = document.createElement('ul');
    node.children.forEach((c) => ul.appendChild(storyNode(c)));
    li.appendChild(ul);
  }
  return li;
}

async function refreshStoryTree() {
  if (!G) return;
  try {
    const data = await getJson('/api/games/' + G.id + '/story');
    const el = $('story-tree');
    el.innerHTML = '';
    if (!data.tree || (!data.tree.children || !data.tree.children.length)) {
      el.innerHTML = '<div style="color:#8b949e;font-size:12px">还没有剧情走向…</div>';
      return;
    }
    const ul = document.createElement('ul');
    ul.appendChild(storyNode(data.tree));
    el.appendChild(ul);
  } catch (e) { /* 忽略 */ }
}

// ---------------- 进入/离开战役 ----------------
function enterGame() {
  if (!G || !me) return;
  $('game-title').textContent = G.name;
  $('chat').innerHTML = '';
  lastMsgId = 0;
  showView('game');
  renderRoster([]);
  loadHistory();
  refreshStoryTree();
  startPoll();
}

function leaveToLobby() {
  clearInterval(pollTimer);
  speakToken++; // 离开战役时停止朗读
  if (currentAudio) {
    try { currentAudio.pause(); } catch (e) { /* ignore */ }
    currentAudio = null;
  }
  G = null;
  lastMsgId = 0;
  myNonces = new Set();
  activeSceneTask = null;
  showView('lobby');
  refreshLobby();
}

// 战役在服务端已失效（如数据库被重置/删除）→ 清理身份并退回大厅
function gameGone() {
  const gid = G ? G.id : null;
  if (gid) sessionStorage.removeItem(identityKey(gid));
  me = null;
  leaveToLobby();
  toast('该战役已失效（可能被重置）。已返回大厅，新建一局吧');
}

async function loadHistory() {
  try {
    const data = await getJson('/api/games/' + G.id + '/messages?after_id=0');
    renderHistory(data.messages);
    let maxId = 0;
    data.messages.forEach((m) => { if (m.id > maxId) maxId = m.id; });
    lastMsgId = maxId;
  } catch (e) {
    renderHistory([]);
  }
}

// ---------------- DM 流式回复（对话 / 掷骰结算共用） ----------------
async function streamDm(body) {
  // 流式获取 DM 回复并渲染；返回完整文本；404 战役失效自动退回大厅
  $('send').disabled = true;
  try {
    const res = await fetch('/api/games/' + G.id + '/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      if (res.status === 404) { gameGone(); return null; }
      let detail = '请求失败';
      try { detail = (await res.json()).detail || detail; } catch (e) { /* ignore */ }
      appendMsgEl(Object.assign(document.createElement('div'), { className: 'msg error', textContent: '出错了：' + detail }));
      return null;
    }
    const dmDiv = document.createElement('div');
    dmDiv.className = 'msg dm';
    appendMsgEl(dmDiv);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let text = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      text += decoder.decode(value, { stream: true });
      dmDiv.innerHTML = renderRich(text); // 流式同步渲染 **关键词** 高亮
      $('chat').scrollTop = $('chat').scrollHeight;
    }
    return text;
  } catch (e) {
    appendMsgEl(Object.assign(document.createElement('div'), { className: 'msg error', textContent: '网络错误：' + e.message }));
    return null;
  } finally {
    $('send').disabled = false;
  }
}

// 文字即掷骰：识别 "掷骰 d20 难度12" / "1d20 dc15" / "检定" 等
function parseDiceText(s) {
  s = s.trim();
  const hasWord = /(掷骰|掷|检定|roll)/i.test(s);
  const fm = s.match(/(\d*)d(\d+)([+-]\d+)?/i);
  if (!hasWord && !fm) return null;
  let formula = '1d20';
  if (fm) {
    const num = fm[1] || '1';
    if (!/^[1-9]\d*$/.test(num)) return null;
    formula = num + 'd' + fm[2] + (fm[3] || '');
  }
  const dcMatch = s.match(/(?:难度|dc)\s*(\d{1,2})/i);
  const difficulty = dcMatch ? parseInt(dcMatch[1], 10) : 12;
  return { formula, difficulty };
}

// ---------------- 发送对话（SSE 流式） ----------------
async function sendMessage() {
  const input = $('input');
  const content = input.value.trim();
  if (!content || !me) return;
  input.value = '';

  // 文字即掷骰
  const diceCmd = parseDiceText(content);
  if (diceCmd) {
    doRoll(diceCmd.formula, diceCmd.difficulty);
    input.focus();
    return;
  }

  const nonce = makeNonce();
  myNonces.add(nonce);
  // 先上屏自己的行动
  appendMsgEl(bubbleFor({ role: 'user', player: me.name, content: '[' + me.name + '] ' + content, color: me.color }));
  const text = await streamDm({ content, player_name: me.name, nonce });
  if (text != null) {
    speakText(text);     // 整段语音播报（自动切块）
    triggerScene(false); // 对话后自动绘场景卡
  }
  input.focus();
}

// ---------------- 掷骰检定 ----------------
function toggleDiceMenu() {
  $('dice-menu').hidden = !$('dice-menu').hidden;
}

async function doRoll(formula, dc) {
  if (!me || !G) { toggleDiceMenu(); return; }
  if (!sessionStorage.getItem('diceTip')) {
    sessionStorage.setItem('diceTip', '1');
    toast('🎲 点数 ≥ 难度(DC) 即成功，掷完 DM 会自动结算');
  }
  const nonce = makeNonce();
  try {
    const data = await postJson('/api/games/' + G.id + '/roll', {
      player_name: me.name, formula, difficulty: dc, nonce,
    });
    myNonces.add(nonce); // 广播轮询回来时跳过，避免重复
    appendMsgEl(bubbleFor(data.message));
    toast('🎲 ' + formula + ' = ' + data.dice.result + ' · ' + (data.dice.success ? '成功' : '失败'));
    refreshStoryTree();
    // 掷完 → 自动请 DM 结算这次检定（门控：等掷完才继续剧情）
    const rNonce = makeNonce();
    myNonces.add(rNonce);
    const text = await streamDm({ content: '', player_name: me.name, nonce: rNonce, resolve: true });
    if (text != null) {
      speakText(text);
      triggerScene(false);
    }
  } catch (e) {
    if (e.status === 404) { gameGone(); return; }
    toast('掷骰失败：' + e.message);
  }
  $('dice-menu').hidden = true;
}

// ---------------- 绑定事件与启动 ----------------
$('btn-new').addEventListener('click', createGame);
$('new-name').addEventListener('keydown', (e) => { if (e.key === 'Enter') createGame(); });
$('btn-back').addEventListener('click', () => { showView('lobby'); refreshLobby(); });
$('btn-home').addEventListener('click', leaveToLobby);
$('scene-regen').addEventListener('click', () => triggerScene(true));
$('send').addEventListener('click', sendMessage);
$('input').addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });
$('dice-btn').addEventListener('click', toggleDiceMenu);
document.querySelectorAll('.dice-presets button').forEach((btn) => {
  btn.addEventListener('click', () => doRoll(btn.dataset.formula, parseInt(btn.dataset.dc, 10)));
});
document.addEventListener('click', (e) => {
  const menu = $('dice-menu');
  if (!menu.hidden && !menu.contains(e.target) && e.target.id !== 'dice-btn') {
    menu.hidden = true;
  }
});

showView('lobby');
refreshLobby();
