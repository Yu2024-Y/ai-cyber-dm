// AI 赛博 DM 前端：SSE 流式对话（S3-1）
const chatEl = document.getElementById('chat');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send');
const SESSION_ID = 1;

function append(role, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
  return div;
}

function scrollBottom() {
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendMessage() {
  const content = inputEl.value.trim();
  if (!content) return;
  append('user', content);
  inputEl.value = '';
  sendBtn.disabled = true;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: SESSION_ID, content: content }),
    });
    if (!res.ok) {
      const err = await res.json();
      append('error', '出错了：' + (err.detail || '请求失败'));
      return;
    }

    // SSE 流式读取：逐段更新 DM 消息（打字机效果）
    const dmDiv = append('dm', '');
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let text = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      text += decoder.decode(value, { stream: true });
      dmDiv.textContent = text;
      scrollBottom();
    }
  } catch (e) {
    append('error', '网络错误：' + e.message);
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

sendBtn.addEventListener('click', sendMessage);
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendMessage();
});
