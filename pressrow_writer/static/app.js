// Press Row Writer's Room — shared app shell
// Handles mode switching, progress header updates, and LLM status indicator.

(function () {
  'use strict';

  // ─── State ───────────────────────────────────────────────────

  const state = {
    currentMode: 'home',
    progress: null,
    llmStatus: null,
    celebrationShown: false,
  };

  // ─── DOM refs ────────────────────────────────────────────────

  const modeButtons = document.querySelectorAll('.wr-mode-btn');
  const modeSections = document.querySelectorAll('.wr-mode');
  const taskChips = document.querySelectorAll('.wr-task-chip');
  const homeCards = document.querySelectorAll('[data-mode-launch]');
  const llmStatusEl = document.getElementById('wr-llm-status');

  // ─── Mode switching ─────────────────────────────────────────

  function switchMode(mode) {
    state.currentMode = mode;
    modeButtons.forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.mode === mode);
    });
    modeSections.forEach((sec) => {
      sec.classList.toggle('is-active', sec.classList.contains(`wr-mode-${mode}`));
    });
    // Fire a custom event so mode-specific scripts can hook in later
    document.dispatchEvent(new CustomEvent('wr:mode-changed', { detail: { mode } }));
  }

  modeButtons.forEach((btn) => {
    btn.addEventListener('click', () => switchMode(btn.dataset.mode));
  });

  homeCards.forEach((card) => {
    card.addEventListener('click', () => switchMode(card.dataset.modeLaunch));
  });

  taskChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const targetMode = chip.dataset.mode;
      if (targetMode) switchMode(targetMode);
    });
  });

  // Global keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Don't hijack keys when typing in a field
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;

    if (e.key === '1') switchMode('chat');
    else if (e.key === '2') switchMode('swipe');
    else if (e.key === '3') switchMode('card');
    else if (e.key === '0' || e.key === 'h' || e.key === 'Escape') switchMode('home');
  });

  // ─── Progress header ────────────────────────────────────────

  let isInitialLoad = true;
  async function loadProgress() {
    try {
      const resp = await fetch('/api/progress');
      if (!resp.ok) return;
      const data = await resp.json();
      state.progress = data;
      // Prevent the initial load from triggering celebration on an already-complete state
      if (isInitialLoad) {
        const allZero =
          (!data.task1 || data.task1.done === 0) &&
          (!data.task2 || data.task2.done === 0) &&
          (!data.task3 || data.task3.done === 0) &&
          (!data.task4 || data.task4.done === 0) &&
          (!data.task5 || data.task5.done === 0);
        if (!allZero) {
          // If user refreshes with everything already complete, don't re-celebrate
          const allMet =
            (data.task1 && data.task1.done >= data.task1.total) &&
            (data.task2 && data.task2.done >= data.task2.total) &&
            (data.task3 && data.task3.done >= data.task3.total) &&
            (data.task4 && data.task4.done >= data.task4.total) &&
            (data.task5 && data.task5.done >= data.task5.total);
          if (allMet) state.celebrationShown = true;
        }
        isInitialLoad = false;
      }
      renderProgress(data);
    } catch (e) {
      console.warn('Failed to load progress:', e);
    }
  }

  function renderProgress(progress) {
    let allComplete = true;
    taskChips.forEach((chip) => {
      const taskKey = chip.dataset.task;
      const task = progress[taskKey];
      if (!task) return;
      const countEl = chip.querySelector('.wr-task-count');
      const fillEl = chip.querySelector('.wr-task-fill');
      if (taskKey === 'task5') {
        countEl.textContent = task.done > 0 ? '✓' : '⚪';
      } else {
        countEl.textContent = `${task.done} / ${task.total}`;
      }
      const pct = task.total > 0 ? Math.min(100, (task.done / task.total) * 100) : 0;
      if (fillEl) fillEl.style.width = pct + '%';
      const isComplete = task.total > 0 && task.done >= task.total;
      chip.classList.toggle('is-complete', isComplete);
      if (!isComplete) allComplete = false;
    });

    // Trigger celebration screen when every task is at or above its target
    if (allComplete && !state.celebrationShown) {
      state.celebrationShown = true;
      showCelebration();
    }
  }

  function showCelebration() {
    // Avoid firing on initial page load when empty files also satisfy "all zero"
    // — only celebrate if the user actually has progress (at least task5 complete
    // or any non-ghost task at 1+)
    const prog = state.progress || {};
    const hasAny =
      (prog.task1 && prog.task1.done > 0) ||
      (prog.task2 && prog.task2.done > 0) ||
      (prog.task3 && prog.task3.done > 0) ||
      (prog.task4 && prog.task4.done > 0) ||
      (prog.task5 && prog.task5.done > 0);
    if (!hasAny) return;

    const overlay = document.createElement('div');
    overlay.className = 'wr-celebration';
    overlay.innerHTML = `
      <div class="wr-celebration-inner">
        <p class="wr-celebration-kicker">Saturday morning, complete.</p>
        <h1 class="wr-celebration-head">The Universe<br><em>is cast.</em></h1>
        <div class="wr-celebration-tasks">
          <div class="wr-celebration-task">T1 · Obsessions <span class="wr-celebration-check">✓</span></div>
          <div class="wr-celebration-task">T2 · Shadow Personas <span class="wr-celebration-check">✓</span></div>
          <div class="wr-celebration-task">T3 · Recurring Fans <span class="wr-celebration-check">✓</span></div>
          <div class="wr-celebration-task">T4 · Feuds <span class="wr-celebration-check">✓</span></div>
          <div class="wr-celebration-task">T5 · Walk-Off Ghost <span class="wr-celebration-check">✓</span></div>
        </div>
        <p class="wr-celebration-note">Press Row 2.0 can read the config files now. Close this window and grind.</p>
        <button class="wr-celebration-close" id="wr-celebration-close">Dismiss</button>
      </div>
    `;
    document.body.appendChild(overlay);
    const close = document.getElementById('wr-celebration-close');
    if (close) close.addEventListener('click', () => overlay.remove());
  }

  // ─── LLM status indicator ───────────────────────────────────

  async function loadLlmStatus() {
    try {
      const resp = await fetch('/api/llm/status');
      if (!resp.ok) return;
      const data = await resp.json();
      state.llmStatus = data;
      renderLlmStatus(data);
    } catch (e) {
      console.warn('Failed to load LLM status:', e);
    }
  }

  function renderLlmStatus(status) {
    if (!llmStatusEl) return;
    if (status.anthropic) {
      llmStatusEl.textContent = 'Sonnet · Online';
      llmStatusEl.classList.add('is-online');
      llmStatusEl.classList.remove('is-offline');
    } else {
      llmStatusEl.textContent = 'Ollama only';
      llmStatusEl.classList.remove('is-online');
    }
  }

  // ─── Public API ─────────────────────────────────────────────

  window.wr = {
    switchMode,
    loadProgress,
    state,
  };

  // ─── Boot ───────────────────────────────────────────────────

  loadProgress();
  loadLlmStatus();
})();
