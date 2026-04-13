// Press Row Writer's Room — Chat mode
// Handles task selection, message sending, committable JSON extraction,
// and commit/discard actions on proposed entries.

(function () {
  'use strict';

  // ─── State ───────────────────────────────────────────────────

  const state = {
    currentTask: 'shadow_personas',
    // histories[task] = [{role, content}, ...]
    histories: {
      shadow_personas: [],
      recurring_fans: [],
      feuds: [],
    },
    isSending: false,
  };

  // ─── DOM refs ────────────────────────────────────────────────

  const taskButtons = document.querySelectorAll('[data-chat-task]');
  const messagesEl = document.getElementById('wr-chat-messages');
  const composerForm = document.getElementById('wr-chat-composer');
  const inputEl = document.getElementById('wr-chat-input');

  if (!messagesEl || !composerForm || !inputEl) return;

  // ─── Task switching ─────────────────────────────────────────

  function switchTask(task) {
    state.currentTask = task;
    taskButtons.forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.chatTask === task);
    });
    // Update placeholder to match task
    const placeholders = {
      shadow_personas: 'Pitch me a shadow persona for the Pirates...',
      recurring_fans: 'Give me a recurring fan — maybe a conspiracy guy...',
      feuds: 'Who should Tony Gedeski feud with?',
    };
    inputEl.placeholder = placeholders[task] || 'Type a message...';
    renderHistory();
  }

  taskButtons.forEach((btn) => {
    btn.addEventListener('click', () => switchTask(btn.dataset.chatTask));
  });

  // ─── Message rendering ──────────────────────────────────────

  function renderHistory() {
    const history = state.histories[state.currentTask] || [];
    if (history.length === 0) {
      messagesEl.innerHTML = `
        <div class="wr-chat-empty">
          <p class="wr-chat-empty-head">Let's cast a character.</p>
          <p class="wr-chat-empty-lede">Tell me what to pitch, and I'll generate candidates in the Morning Lineup voice.</p>
        </div>
      `;
      return;
    }
    messagesEl.innerHTML = '';
    history.forEach((msg, i) => {
      const bubble = renderBubble(msg, i);
      messagesEl.appendChild(bubble);
    });
    scrollToBottom();
  }

  function renderBubble(msg, index) {
    const bubble = document.createElement('div');
    bubble.className = `wr-chat-bubble wr-chat-bubble-${msg.role}`;

    const label = document.createElement('div');
    label.className = 'wr-chat-bubble-label';
    label.textContent = msg.role === 'user' ? 'You' : 'Casting Director';
    bubble.appendChild(label);

    const body = document.createElement('div');
    body.className = 'wr-chat-bubble-body';
    body.textContent = stripJsonBlocks(msg.content);
    bubble.appendChild(body);

    // If this is an assistant message with committable entries, render cards
    if (msg.role === 'assistant' && msg.committable && msg.committable.length > 0) {
      msg.committable.forEach((entry, entryIdx) => {
        const card = renderCommittableCard(entry, index, entryIdx, msg.committedIndices || []);
        bubble.appendChild(card);
      });
    }
    return bubble;
  }

  function stripJsonBlocks(text) {
    // Remove ```json ... ``` fenced blocks for display (they're shown as cards)
    return text.replace(/```(?:json)?\s*[\s\S]*?```/g, '').trim();
  }

  function renderCommittableCard(entry, msgIdx, entryIdx, committedIndices) {
    const card = document.createElement('div');
    card.className = 'wr-chat-committable';
    const isCommitted = committedIndices.includes(entryIdx);
    if (isCommitted) card.classList.add('is-committed');

    const header = document.createElement('div');
    header.className = 'wr-chat-committable-header';
    header.textContent = describeEntry(entry);
    card.appendChild(header);

    const preview = document.createElement('pre');
    preview.className = 'wr-chat-committable-preview';
    preview.textContent = JSON.stringify(entry, null, 2);
    card.appendChild(preview);

    const actions = document.createElement('div');
    actions.className = 'wr-chat-committable-actions';

    if (isCommitted) {
      const status = document.createElement('span');
      status.className = 'wr-chat-committed-label';
      status.textContent = '✓ Committed';
      actions.appendChild(status);
    } else {
      const accept = document.createElement('button');
      accept.className = 'wr-chat-btn wr-chat-btn-accept';
      accept.textContent = '✓ Accept';
      accept.addEventListener('click', () => commitEntry(entry, msgIdx, entryIdx, card));
      actions.appendChild(accept);

      const discard = document.createElement('button');
      discard.className = 'wr-chat-btn wr-chat-btn-discard';
      discard.textContent = '✗ Discard';
      discard.addEventListener('click', () => discardEntry(msgIdx, entryIdx, card));
      actions.appendChild(discard);
    }

    card.appendChild(actions);
    return card;
  }

  function describeEntry(entry) {
    if (!entry || typeof entry !== 'object') return 'Entry';
    if (entry.team_slug && entry.name) return `${entry.team_slug.toUpperCase()} · ${entry.name}`;
    if (entry.name && entry.team_slug === undefined && entry.voice) return entry.name;
    if (entry.id && entry.writers) return `Feud: ${entry.writers.join(' vs ')}`;
    return 'Entry';
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ─── Send message ───────────────────────────────────────────

  async function sendMessage(text) {
    if (!text || state.isSending) return;
    state.isSending = true;

    const history = state.histories[state.currentTask];
    // Append user message
    history.push({ role: 'user', content: text });
    renderHistory();

    // Show typing indicator
    const typing = document.createElement('div');
    typing.className = 'wr-chat-bubble wr-chat-bubble-assistant wr-chat-typing';
    typing.innerHTML = '<div class="wr-chat-bubble-label">Casting Director</div><div class="wr-chat-bubble-body">typing…</div>';
    messagesEl.appendChild(typing);
    scrollToBottom();

    try {
      const resp = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: state.currentTask,
          history: history.slice(0, -1).map((m) => ({ role: m.role, content: m.content })),
          user_message: text,
        }),
      });

      typing.remove();

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        history.push({
          role: 'assistant',
          content: `⚠ ${err.error || 'Request failed'}`,
          committable: [],
        });
        renderHistory();
        return;
      }

      const data = await resp.json();
      history.push({
        role: 'assistant',
        content: data.response || '',
        committable: data.committable || [],
        committedIndices: [],
      });
      renderHistory();
    } catch (e) {
      typing.remove();
      history.push({
        role: 'assistant',
        content: `⚠ Network error: ${e.message}`,
        committable: [],
      });
      renderHistory();
    } finally {
      state.isSending = false;
      inputEl.focus();
    }
  }

  composerForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = '';
    sendMessage(text);
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      composerForm.requestSubmit();
    }
  });

  // ─── Commit / discard ───────────────────────────────────────

  async function commitEntry(entry, msgIdx, entryIdx, cardEl) {
    cardEl.classList.add('is-committing');
    try {
      const resp = await fetch(`/api/chat/commit/${state.currentTask}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry }),
      });

      if (resp.status === 409) {
        const err = await resp.json();
        const replace = confirm(`${err.error}\n\nReplace existing?`);
        if (!replace) {
          cardEl.classList.remove('is-committing');
          return;
        }
        // Retry with replace flag
        const retry = await fetch(`/api/chat/commit/${state.currentTask}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entry, replace: true }),
        });
        if (!retry.ok) {
          alert('Commit still failed after replace attempt.');
          cardEl.classList.remove('is-committing');
          return;
        }
      } else if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        alert(`Commit failed: ${err.error || resp.statusText}`);
        cardEl.classList.remove('is-committing');
        return;
      }

      // Mark committed in state
      const msg = state.histories[state.currentTask][msgIdx];
      if (msg) {
        msg.committedIndices = msg.committedIndices || [];
        if (!msg.committedIndices.includes(entryIdx)) {
          msg.committedIndices.push(entryIdx);
        }
      }
      cardEl.classList.remove('is-committing');
      cardEl.classList.add('is-committed');

      // Refresh card in-place
      const newCard = renderCommittableCard(entry, msgIdx, entryIdx, msg.committedIndices);
      cardEl.replaceWith(newCard);

      // Refresh global progress header
      if (window.wr && typeof window.wr.loadProgress === 'function') {
        window.wr.loadProgress();
      }
    } catch (e) {
      alert(`Commit failed: ${e.message}`);
      cardEl.classList.remove('is-committing');
    }
  }

  function discardEntry(msgIdx, entryIdx, cardEl) {
    cardEl.style.opacity = '0.35';
    cardEl.style.pointerEvents = 'none';
    const label = cardEl.querySelector('.wr-chat-committable-header');
    if (label) label.textContent = '✗ Discarded';
  }

  // ─── Mode change hook ───────────────────────────────────────

  document.addEventListener('wr:mode-changed', (e) => {
    if (e.detail && e.detail.mode === 'chat') {
      setTimeout(() => inputEl.focus(), 50);
    }
  });

  // ─── Init ───────────────────────────────────────────────────

  switchTask('shadow_personas');
})();
