// AI 赛博 DM 前端 MVP：对话交互
const chatEl = document.getElementById('chat');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send');

function append(role, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendMessage() {
  const content = inputEl.value.trim();
  if (!content) return;
  append('user', content);
  inputEl.value = '';

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: 1, content: content }),
    });
    if (!res.ok) {
      const err = await res.json();
      append('error', '出错了：' + (err.detail || '请求失败'));
      return;
    }
    // 读取完整剧情文本（MVP 非流式展示，SSE 打字机在 Sprint 3 实现）
    const text = await res.text();
    append('dm', text);
  } catch (e) {
    append('error', '网络错误：' + e.message);
  }
}

sendBtn.addEventListener('click', sendMessage);
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendMessage();
});
