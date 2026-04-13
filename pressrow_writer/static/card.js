// Press Row Writer's Room — Card mode (Walk-Off Ghost conjuring booth)
// Task 5. Full-screen black page with side oracle that whispers cryptic
// fragments. User builds the voice sample by accumulating accepted lines.

(function () {
  'use strict';

  const state = {
    name: 'Section 214',
    voice: '',
    samples: [],
    currentFragment: null,
    isConjuring: false,
  };

  const container = document.getElementById('wr-card-container');
  if (!container) return;

  // ─── Render ──────────────────────────────────────────────────

  function render() {
    const samplesHtml = state.samples.length
      ? state.samples
          .map(
            (s, i) => `
              <div class="wr-ghost-sample">
                <span class="wr-ghost-sample-num">${String(i + 1).padStart(2, '0')}</span>
                <span class="wr-ghost-sample-text">${escapeHtml(s)}</span>
                <button class="wr-ghost-sample-remove" data-idx="${i}">×</button>
              </div>`
          )
          .join('')
      : '<div class="wr-ghost-samples-empty">The voice is empty. Ask the oracle.</div>';

    const currentHtml = state.currentFragment
      ? `
        <div class="wr-ghost-current">
          <div class="wr-ghost-current-label">Oracle whispers</div>
          <div class="wr-ghost-current-text">${escapeHtml(state.currentFragment)}</div>
          <div class="wr-ghost-current-actions">
            <button class="wr-ghost-btn wr-ghost-btn-accept" id="wr-ghost-accept">
              ✓ Keep
            </button>
            <button class="wr-ghost-btn wr-ghost-btn-reject" id="wr-ghost-reject">
              ✗ Dismiss
            </button>
            <button class="wr-ghost-btn wr-ghost-btn-again" id="wr-ghost-again">
              Whisper again
            </button>
          </div>
        </div>
      `
      : `
        <div class="wr-ghost-idle">
          <button class="wr-ghost-btn wr-ghost-btn-conjure" id="wr-ghost-conjure">
            ${state.isConjuring ? 'Listening…' : 'Ask the oracle'}
          </button>
        </div>
      `;

    const canCommit = state.samples.length >= 1 && state.voice.trim().length > 0 && state.name.trim().length > 0;

    container.innerHTML = `
      <div class="wr-ghost-stage">
        <header class="wr-ghost-head">
          <div class="wr-ghost-kicker">Task 5 · Walk-Off Ghost</div>
          <h2 class="wr-ghost-title">The Conjuring Booth</h2>
          <p class="wr-ghost-lede">A cryptic persona that only posts after dramatic game endings. Never names players. Always mentions a physical detail of the venue. The oracle whispers fragments; you accumulate the voice.</p>
        </header>

        <div class="wr-ghost-form">
          <label class="wr-ghost-field">
            <span class="wr-ghost-field-label">Name</span>
            <input type="text" id="wr-ghost-name" value="${escapeHtml(state.name)}" placeholder="Section 214" />
          </label>
          <label class="wr-ghost-field">
            <span class="wr-ghost-field-label">Voice (one-sentence description)</span>
            <textarea id="wr-ghost-voice" rows="2" placeholder="cryptic, observational, second-person, never names players, always mentions a physical detail of the venue">${escapeHtml(state.voice)}</textarea>
          </label>
        </div>

        ${currentHtml}

        <div class="wr-ghost-samples-box">
          <div class="wr-ghost-samples-head">
            <span class="wr-ghost-samples-label">Sample Tweets (${state.samples.length})</span>
            <span class="wr-ghost-samples-hint">Keep 3-5 that nail the voice</span>
          </div>
          ${samplesHtml}
        </div>

        <div class="wr-ghost-commit-row">
          <button class="wr-ghost-commit-btn" id="wr-ghost-commit" ${canCommit ? '' : 'disabled'}>
            ${canCommit ? 'Seal the ghost' : 'Need name + voice + ≥1 sample'}
          </button>
        </div>
      </div>
    `;

    // Wire events
    const conjureBtn = document.getElementById('wr-ghost-conjure');
    if (conjureBtn) conjureBtn.addEventListener('click', conjure);

    const acceptBtn = document.getElementById('wr-ghost-accept');
    if (acceptBtn) acceptBtn.addEventListener('click', acceptFragment);

    const rejectBtn = document.getElementById('wr-ghost-reject');
    if (rejectBtn) rejectBtn.addEventListener('click', rejectFragment);

    const againBtn = document.getElementById('wr-ghost-again');
    if (againBtn) againBtn.addEventListener('click', conjure);

    const commitBtn = document.getElementById('wr-ghost-commit');
    if (commitBtn) commitBtn.addEventListener('click', commitGhost);

    const nameInput = document.getElementById('wr-ghost-name');
    if (nameInput) nameInput.addEventListener('input', (e) => {
      state.name = e.target.value;
      updateCommitButtonState();
    });

    const voiceInput = document.getElementById('wr-ghost-voice');
    if (voiceInput) voiceInput.addEventListener('input', (e) => {
      state.voice = e.target.value;
      updateCommitButtonState();
    });

    container.querySelectorAll('.wr-ghost-sample-remove').forEach((btn) => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.dataset.idx, 10);
        state.samples.splice(idx, 1);
        render();
      });
    });
  }

  function updateCommitButtonState() {
    const btn = document.getElementById('wr-ghost-commit');
    if (!btn) return;
    const canCommit = state.samples.length >= 1 && state.voice.trim().length > 0 && state.name.trim().length > 0;
    btn.disabled = !canCommit;
    btn.textContent = canCommit ? 'Seal the ghost' : 'Need name + voice + ≥1 sample';
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

  // ─── Oracle ──────────────────────────────────────────────────

  async function conjure() {
    if (state.isConjuring) return;
    state.isConjuring = true;
    const btn = document.getElementById('wr-ghost-conjure');
    const again = document.getElementById('wr-ghost-again');
    if (btn) btn.textContent = 'Listening…';
    if (again) again.textContent = 'Listening…';

    try {
      const resp = await fetch('/api/card/ghost/oracle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context: '',
          existing_samples: state.samples,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        alert(`Oracle failed: ${err.error || resp.statusText}`);
        return;
      }
      const data = await resp.json();
      state.currentFragment = data.fragment || '';
    } catch (e) {
      alert(`Oracle failed: ${e.message}`);
    } finally {
      state.isConjuring = false;
      render();
    }
  }

  function acceptFragment() {
    if (!state.currentFragment) return;
    state.samples.push(state.currentFragment);
    state.currentFragment = null;
    render();
  }

  function rejectFragment() {
    state.currentFragment = null;
    render();
  }

  // ─── Commit ──────────────────────────────────────────────────

  async function commitGhost() {
    if (state.samples.length < 1 || !state.voice.trim() || !state.name.trim()) {
      alert('Need name, voice, and at least 1 sample.');
      return;
    }
    try {
      const resp = await fetch('/api/card/ghost/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: state.name.trim(),
          voice: state.voice.trim(),
          sample_tweets: state.samples,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        alert(`Commit failed: ${err.error || resp.statusText}`);
        return;
      }
      const data = await resp.json();
      if (window.wr && typeof window.wr.loadProgress === 'function') {
        window.wr.loadProgress();
      }
      // Brief celebration
      container.innerHTML = `
        <div class="wr-ghost-sealed">
          <div class="wr-ghost-sealed-kicker">Task 5 · Complete</div>
          <h2 class="wr-ghost-sealed-name">${escapeHtml(state.name)}</h2>
          <p class="wr-ghost-sealed-voice">${escapeHtml(state.voice)}</p>
          <div class="wr-ghost-sealed-samples">
            ${state.samples.map((s) => `<div class="wr-ghost-sealed-sample">${escapeHtml(s)}</div>`).join('')}
          </div>
          <p class="wr-ghost-sealed-note">The ghost is sealed in <code>pressrow/config/cast.json</code>.</p>
        </div>
      `;
    } catch (e) {
      alert(`Commit failed: ${e.message}`);
    }
  }

  // ─── Mode change hook ────────────────────────────────────────

  document.addEventListener('wr:mode-changed', (e) => {
    if (e.detail && e.detail.mode === 'card') {
      // Fresh state on entry if nothing committed yet
      if (!state.currentFragment && state.samples.length === 0) {
        render();
      }
    }
  });

  // ─── Init ────────────────────────────────────────────────────

  render();
})();
