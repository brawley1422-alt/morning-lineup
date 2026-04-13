// Press Row Writer's Room — Swipe mode
// Full-screen card stack for Task 1 obsession curation.
// Keyboard: ← reject · → accept · space = anchor.

(function () {
  'use strict';

  const state = {
    current: null,      // the candidate currently displayed
    isLoading: false,
    isProcessing: false,
    hasBatch: true,     // toggled to false if /api/swipe/next says no batch
    done: false,
  };

  const container = document.getElementById('wr-swipe-container');
  if (!container) return;

  // ─── Render ──────────────────────────────────────────────────

  function renderEmpty() {
    container.innerHTML = `
      <div class="wr-swipe-empty">
        <p class="wr-swipe-empty-kicker">Task 1 · Obsessions</p>
        <h2 class="wr-swipe-empty-head">No candidates yet.</h2>
        <p class="wr-swipe-empty-lede">The swipe deck pulls from a pre-generated batch. Run this in your terminal from the repo root:</p>
        <pre class="wr-swipe-empty-cmd">python3 -m pressrow_writer batch</pre>
        <p class="wr-swipe-empty-note">This calls Sonnet once per writer (~90 calls) and writes ~810 candidates to <code>pressrow_writer/state/batch_obsessions.json</code>. Takes ~15-25 minutes. Then refresh this page.</p>
      </div>
    `;
  }

  function renderLoading() {
    container.innerHTML = `
      <div class="wr-swipe-loading">
        <p>Dealing the next candidate…</p>
      </div>
    `;
  }

  function renderDone() {
    container.innerHTML = `
      <div class="wr-swipe-empty">
        <p class="wr-swipe-empty-kicker">Task 1 · Obsessions</p>
        <h2 class="wr-swipe-empty-head">Deck cleared.</h2>
        <p class="wr-swipe-empty-lede">Every candidate has been seen. Task 1 is complete (or close enough). Jump to another task via the header chips.</p>
      </div>
    `;
  }

  function renderCard(data) {
    const writer = data.writer;
    const candidate = data.candidate;
    const primary = (writer.colors && writer.colors.primary) || '#2a3142';
    const accent = (writer.colors && writer.colors.accent) || '#c9a24a';

    const triggerHtml = (candidate.trigger_phrases || [])
      .map((t) => `<span class="wr-swipe-trigger">${escapeHtml(t)}</span>`)
      .join('');

    container.innerHTML = `
      <div class="wr-swipe-stage">
        <div class="wr-swipe-progress">
          <span class="wr-swipe-progress-label">Writer ${writer.team_abbr} · ${escapeHtml(writer.name)}</span>
          <span class="wr-swipe-progress-count">${data.current_obsession_count} committed · ${data.remaining_for_writer} left for this writer · ${data.total_remaining} total unseen</span>
        </div>

        <div class="wr-swipe-card" style="--card-primary:${primary};--card-accent:${accent}">
          <div class="wr-swipe-card-team">
            <div class="wr-swipe-card-cap" style="background:${primary}">${escapeHtml(writer.initials)}</div>
            <div class="wr-swipe-card-team-meta">
              <div class="wr-swipe-card-name">${escapeHtml(writer.name)}</div>
              <div class="wr-swipe-card-role">${escapeHtml(writer.role || '')}</div>
            </div>
            <div class="wr-swipe-card-abbr">${escapeHtml(writer.team_abbr)}</div>
          </div>

          <div class="wr-swipe-card-voice">
            <span class="wr-swipe-card-voice-label">Voice Sample</span>
            <em>${escapeHtml(writer.voice_sample || '')}</em>
          </div>

          <div class="wr-swipe-card-obsession">
            <div class="wr-swipe-card-topic">${escapeHtml(candidate.topic)}</div>
            <div class="wr-swipe-card-angle">${escapeHtml(candidate.angle)}</div>
            <div class="wr-swipe-card-triggers">${triggerHtml}</div>
          </div>
        </div>

        <div class="wr-swipe-actions">
          <button class="wr-swipe-btn wr-swipe-btn-reject" id="wr-swipe-reject">
            <span class="wr-swipe-btn-icon">✗</span>
            <span class="wr-swipe-btn-label">Reject</span>
            <span class="wr-swipe-btn-hint">←</span>
          </button>
          <button class="wr-swipe-btn wr-swipe-btn-anchor" id="wr-swipe-anchor">
            <span class="wr-swipe-btn-icon">🪨</span>
            <span class="wr-swipe-btn-label">Anchor</span>
            <span class="wr-swipe-btn-hint">Space</span>
          </button>
          <button class="wr-swipe-btn wr-swipe-btn-accept" id="wr-swipe-accept">
            <span class="wr-swipe-btn-icon">✓</span>
            <span class="wr-swipe-btn-label">Accept</span>
            <span class="wr-swipe-btn-hint">→</span>
          </button>
        </div>
      </div>
    `;

    document.getElementById('wr-swipe-reject').addEventListener('click', () => action('reject'));
    document.getElementById('wr-swipe-accept').addEventListener('click', () => action('accept'));
    document.getElementById('wr-swipe-anchor').addEventListener('click', () => action('anchor'));
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // ─── API ─────────────────────────────────────────────────────

  async function loadNext() {
    if (state.isLoading) return;
    state.isLoading = true;
    renderLoading();

    try {
      const resp = await fetch('/api/swipe/next');
      if (resp.status === 404) {
        state.hasBatch = false;
        renderEmpty();
        return;
      }
      if (!resp.ok) {
        container.innerHTML = `<div class="wr-swipe-error">Error: ${resp.statusText}</div>`;
        return;
      }
      const data = await resp.json();
      if (data.done) {
        state.done = true;
        renderDone();
        return;
      }
      state.current = data;
      renderCard(data);
    } catch (e) {
      container.innerHTML = `<div class="wr-swipe-error">Error: ${e.message}</div>`;
    } finally {
      state.isLoading = false;
    }
  }

  async function action(kind) {
    if (!state.current || state.isProcessing) return;
    state.isProcessing = true;
    const index = state.current.index;
    const endpoint = {
      reject: '/api/swipe/reject',
      accept: '/api/swipe/accept',
      anchor: '/api/swipe/anchor',
    }[kind];

    // Animate card off
    const card = container.querySelector('.wr-swipe-card');
    if (card) {
      card.classList.add(`is-${kind}`);
    }

    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        alert(`Action failed: ${err.error || resp.statusText}`);
        state.isProcessing = false;
        return;
      }
      const data = await resp.json();

      // Refresh progress header
      if (window.wr && typeof window.wr.loadProgress === 'function') {
        window.wr.loadProgress();
      }

      // Brief delay to let the animation play
      await new Promise((r) => setTimeout(r, 260));
    } catch (e) {
      alert(`Action failed: ${e.message}`);
      state.isProcessing = false;
      return;
    }

    state.isProcessing = false;
    state.current = null;
    loadNext();
  }

  // ─── Keyboard shortcuts ──────────────────────────────────────

  document.addEventListener('keydown', (e) => {
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;

    // Only react when swipe mode is active
    const swipeActive = document.querySelector('.wr-mode-swipe.is-active');
    if (!swipeActive) return;
    if (!state.current) return;

    if (e.key === 'ArrowLeft') action('reject');
    else if (e.key === 'ArrowRight') action('accept');
    else if (e.key === ' ') { e.preventDefault(); action('anchor'); }
  });

  // ─── Mode change hook ────────────────────────────────────────

  document.addEventListener('wr:mode-changed', (e) => {
    if (e.detail && e.detail.mode === 'swipe') {
      // Reset and load fresh when entering swipe mode
      if (!state.current && !state.done) {
        loadNext();
      }
    }
  });

  // ─── Init ────────────────────────────────────────────────────

  // Render empty state initially — loadNext fires when user switches to swipe mode
  renderEmpty();
})();
