// Shared visual devices: epistemic stamps, the discovery ladder, status pills, the agent block.

import { h, hashCode, copyText } from './util.js';

export const TAGS = {
  observed: 'read straight off the data',
  computed: 'derived by code you can rerun',
  inferred: 'a reasoned step beyond the data',
  speculated: 'an idea worth testing, not yet evidence',
};

/** A rubber-stamp label for an epistemic tag. Each instance is inked at a slightly different angle. */
export function stamp(tag, seed = '') {
  const t = TAGS[tag] ? tag : 'unknown';
  const rot = -2 + ((hashCode(seed + tag) % 100) / 100 - 0.5) * 1.6;
  return h('span', { class: `stamp stamp-${t}`, style: { '--rot': `${rot.toFixed(2)}deg` }, title: TAGS[t] ? `${t}: ${TAGS[t]}` : 'untagged' }, t);
}

export function stampLegend() {
  return h('dl', { class: 'stamp-legend' }, Object.entries(TAGS).map(([k, v]) => h('div', null, h('dt', null, stamp(k, 'legend')), h('dd', null, v))));
}

// ---- the discovery ladder ---------------------------------------------------------------------
export const RUNGS = ['observation', 'anomaly', 'reproduced', 'interpreted', 'validated'];
export const EXITS = ['artifact', 'closed'];
const RUNG_NOTE = {
  observation: 'data gathered',
  anomaly: 'something is odd',
  reproduced: 'seen independently',
  interpreted: 'an explanation leads',
  validated: 'a prediction came true',
  artifact: 'it was the instrument',
  closed: 'explained, case closed',
};

export function ladder(status, { compact = false } = {}) {
  const at = RUNGS.indexOf(status);
  const exitAt = EXITS.indexOf(status);
  const el = h('div', { class: `ladder ${compact ? 'is-compact' : ''} ${exitAt >= 0 ? 'is-exited' : ''}`, role: 'img', 'aria-label': `Discovery ladder: ${status || 'unknown'}` },
    h('ol', { class: 'ladder-track' }, RUNGS.map((r, i) => h('li', {
      class: `rung ${i < at ? 'is-past' : ''} ${i === at ? 'is-here' : ''}`, title: `${r}: ${RUNG_NOTE[r]}`,
    }, h('span', { class: 'rung-dot' }), h('span', { class: 'rung-label' }, r)))),
    h('ul', { class: 'ladder-exits' }, EXITS.map((x) => h('li', { class: `exit ${x === status ? 'is-here' : ''}`, title: `${x}: ${RUNG_NOTE[x]}` },
      h('span', { class: 'rung-dot' }), h('span', { class: 'rung-label' }, x)))),
  );
  return el;
}

export function statusPill(status) {
  const known = ['live', 'favored', 'disfavored', 'rejected'];
  const st = known.includes(status) ? status : 'live';
  return h('span', { class: `pill pill-${st}` }, st);
}

// ---- "Investigate this with your agent" -------------------------------------------------------
export const MCP_CMD = 'claude mcp add oddsky -- uvx oddsky mcp';
export const REPO = 'https://github.com/oddsky-org/oddsky';
export const starterPrompt = (id) => `Open Oddsky case ${id}. Run the skeptic first, then try to break the leading hypothesis. Tag every claim honestly.`;

function copyRow(text, label, { prompt = false } = {}) {
  const btn = h('button', { type: 'button', class: 'copy', 'aria-label': `Copy ${label}` }, 'Copy');
  btn.addEventListener('click', () => copyText(text, btn));
  return h('div', { class: `copy-row ${prompt ? 'is-prompt' : ''}` }, h(prompt ? 'p' : 'code', { class: prompt ? 'prompt-text' : 'cmd' }, prompt ? null : h('span', { class: 'cmd-dollar', 'aria-hidden': 'true' }, '$ '), text), btn);
}

export function agentBlock(caseId) {
  return h('section', { class: 'agent', 'aria-labelledby': `agent-${caseId}` },
    h('p', { class: 'agent-kicker' }, 'Your turn'),
    h('h2', { class: 'agent-title', id: `agent-${caseId}` }, 'Investigate this with your agent'),
    h('ol', { class: 'agent-steps' },
      h('li', null, h('span', { class: 'step-label' }, 'Give your agent the observatory'), copyRow(MCP_CMD, 'install command'),
        h('p', { class: 'agent-note' }, 'Works with any MCP-capable agent: Claude Code, Codex, Cursor, or a local model. Oddsky ships the tools and the data, not the AI.')),
      h('li', null, h('span', { class: 'step-label' }, 'Then ask it'), copyRow(starterPrompt(caseId), 'starter prompt', { prompt: true }))),
    h('p', { class: 'agent-fork' }, 'or ', h('a', { href: `${REPO}/tree/main/cases/${caseId}`, rel: 'noopener', target: '_blank' }, 'fork the case on GitHub'),
      ' — a case is a directory; review is a pull request.'),
  );
}

export function emptyNote(title, ...body) {
  return h('div', { class: 'empty' }, h('p', { class: 'empty-title' }, title), ...body.map((b) => (typeof b === 'string' ? h('p', null, b) : b)));
}

export function sectionHead(id, title, count, lede) {
  return h('header', { class: 'section-head' },
    h('h2', { id: `h-${id}` }, title, count != null ? h('span', { class: 'count' }, String(count)) : null),
    lede ? h('p', { class: 'section-lede' }, lede) : null);
}
