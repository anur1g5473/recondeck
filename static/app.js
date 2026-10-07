const appEl = document.getElementById('app');
const tokenMeta = document.querySelector('meta[name="token"]');
const token = tokenMeta ? tokenMeta.getAttribute('content') : '';
const TERMS_VERSION = 1;
const TERMS_STORAGE_KEY = `recondeck_terms_v${TERMS_VERSION}`;
const state = {
  scans: [],
  lastScanId: '',
  activeView: 'home',
  scanState: null,
  termsText: '',
};

const el = (tag, { className, text, attrs = {} } = {}, children = []) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value !== undefined && value !== null) node.setAttribute(key, value);
  });
  children.forEach((child) => node.appendChild(child));
  return node;
};

function setTokenHeader(headers = {}) {
  headers['X-ReconDeck-Token'] = token;
  return headers;
}

async function api(path, options = {}) {
  const requestOptions = { headers: setTokenHeader(options.headers || {}) };
  if (options.method) requestOptions.method = options.method;
  if (options.body !== undefined) requestOptions.body = options.body;
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    requestOptions.headers['Content-Type'] = 'application/json';
    requestOptions.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, requestOptions);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed (${response.status})`);
  }
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return response.json();
  return response.text();
}

async function fetchTermsText() {
  if (state.termsText) return state.termsText;
  const response = await fetch(`/terms?token=${encodeURIComponent(token)}`);
  if (!response.ok) {
    throw new Error('Could not load the terms screen.');
  }
  state.termsText = await response.text();
  return state.termsText;
}

async function loadScans() {
  const scans = await api('/api/scans');
  state.scans = scans;
}

function createFlagDots(flagCounts = {}) {
  return [
    el('span', { className: 'dot green', attrs: { title: `Green: ${flagCounts.green ?? 0}` } }),
    el('span', { className: 'dot yellow', attrs: { title: `Yellow: ${flagCounts.yellow ?? 0}` } }),
    el('span', { className: 'dot red', attrs: { title: `Red: ${flagCounts.red ?? 0}` } }),
    el('span', { className: 'dot grey', attrs: { title: `Grey: ${flagCounts.grey ?? 0}` } }),
  ];
}

function renderScanList() {
  const list = el('ul', { className: 'scan-list' }, []);
  if (!state.scans.length) {
    list.appendChild(el('li', { className: 'scan-item' }, [
      el('div', { className: 'row' }, [
        el('strong', { text: 'No past scans' }),
      ]),
      el('div', { className: 'meta', text: 'Start your first scan' })
    ]));
    return list;
  }

  state.scans.forEach((scan) => {
    const item = el('li', { className: 'scan-item' }, [
      el('div', { className: 'row' }, [
        el('strong', { text: scan.domain || scan.id }),
        el('span', { className: 'small-muted', text: scan.status || 'queued' })
      ]),
      el('div', { className: 'meta', text: new Date(scan.date || Date.now()).toLocaleString() }),
      el('div', { className: 'flags' }, createFlagDots(scan.flag_counts || {})),
      el('button', { className: 'small-btn', text: 'Open' }, [])
    ]);
    item.querySelector('button').addEventListener('click', async () => {
      state.lastScanId = scan.id;
      try {
        const details = await api(`/api/scans/${scan.id}`);
        state.scanState = details;
        state.activeView = 'report';
        render();
      } catch (error) {
        alert(error.message || 'Could not load scan');
      }
    });
    list.appendChild(item);
  });
  return list;
}

function renderTermsView() {
  const panel = el('div', { className: 'terms-card' }, [
    el('h1', { className: 'form-title', text: 'ReconDeck Terms of Use' }),
    el('div', { className: 'terms-box' }, [
      el('pre', { className: 'terms-text', text: state.termsText || 'Loading terms…' })
    ]),
    el('label', { className: 'check-row' }, [
      el('input', { attrs: { type: 'checkbox', id: 'termsCheckbox' } }),
      el('span', { text: 'I have read and agree to these terms' })
    ]),
    el('button', { className: 'primary-btn', attrs: { id: 'acceptTermsButton', type: 'button', disabled: 'disabled' }, text: 'Continue' })
  ]);

  const checkbox = panel.querySelector('#termsCheckbox');
  const button = panel.querySelector('#acceptTermsButton');
  checkbox.addEventListener('change', () => {
    button.disabled = !checkbox.checked;
  });
  button.addEventListener('click', async () => {
    if (!checkbox.checked) return;
    try {
      await api('/api/accept-terms', { method: 'POST', body: { terms_version: TERMS_VERSION } });
      localStorage.setItem(TERMS_STORAGE_KEY, String(TERMS_VERSION));
      state.activeView = 'home';
      render();
    } catch (error) {
      alert(error.message || 'Could not save terms acceptance.');
    }
  });

  return panel;
}

function renderHome() {
  const panel = el('div', { className: 'form-card' }, [
    el('h1', { className: 'form-title', text: 'Scan everything' }),
    el('div', { className: 'field' }, [
      el('label', { text: 'Target' }),
      el('input', { className: 'input', attrs: { type: 'text', id: 'targetInput', placeholder: 'example.com or a URL', value: 'example.com' } })
    ]),
    el('div', { className: 'field' }, [
      el('label', { text: 'Wordlist' }),
      el('div', { className: 'wordlist-row' }, [
        el('label', { className: 'check-row' }, [
          el('input', { attrs: { type: 'radio', name: 'wordlist', checked: 'checked', value: 'small' } }),
          el('span', { text: 'small' })
        ]),
        el('label', { className: 'check-row' }, [
          el('input', { attrs: { type: 'radio', name: 'wordlist', value: 'medium' } }),
          el('span', { text: 'medium' })
        ]),
        el('label', { className: 'check-row' }, [
          el('input', { attrs: { type: 'radio', name: 'wordlist', value: 'large' } }),
          el('span', { text: 'large' })
        ])
      ])
    ]),
    el('label', { className: 'check-row' }, [
      el('input', { attrs: { type: 'checkbox', id: 'activeCheckbox' } }),
      el('span', { text: 'Active probing (zone transfer, brute force, version queries)' })
    ]),
    el('div', { className: 'warning-box', text: 'Sends many queries to the target\'s own servers. Only use on domains you are allowed to test.' }),
    el('label', { className: 'check-row' }, [
      el('input', { attrs: { type: 'checkbox', id: 'authorizedCheckbox' } }),
      el('span', { text: 'I own this domain or have written permission to test it' })
    ]),
    el('button', { className: 'primary-btn', attrs: { id: 'scanButton', type: 'button' }, text: 'Scan everything' })
  ]);

  const targetInput = panel.querySelector('#targetInput');
  const activeCheckbox = panel.querySelector('#activeCheckbox');
  const authorizedCheckbox = panel.querySelector('#authorizedCheckbox');
  const scanButton = panel.querySelector('#scanButton');

  const refreshState = () => {
    const hasTarget = targetInput.value.trim().length > 0;
    const canSubmit = hasTarget && authorizedCheckbox.checked;
    scanButton.disabled = !canSubmit;
  };

  targetInput.addEventListener('input', refreshState);
  activeCheckbox.addEventListener('change', () => {
    if (activeCheckbox.checked && !authorizedCheckbox.checked) {
      authorizedCheckbox.checked = true;
    }
    refreshState();
  });
  authorizedCheckbox.addEventListener('change', refreshState);

  scanButton.addEventListener('click', async () => {
    const target = targetInput.value.trim();
    const active = activeCheckbox.checked;
    const authorized = authorizedCheckbox.checked;
    const selectedWordlist = document.querySelector('input[name="wordlist"]:checked')?.value || 'small';
    scanButton.disabled = true;
    try {
      const response = await api('/api/scans', {
        method: 'POST',
        body: { target, wordlist: selectedWordlist, active, authorized }
      });
      state.lastScanId = response.scan_id;
      state.activeView = 'scan';
      state.scanState = { id: response.scan_id, status: 'running', target: { hostname: target }, progress: { done: 0, total: 10 }, findings: [] };
      render();
      pollScan(response.scan_id);
    } catch (error) {
      alert(error.message || 'Scan failed');
    } finally {
      refreshState();
    }
  });

  return panel;
}

async function pollScan(scanId) {
  try {
    const details = await api(`/api/scans/${scanId}`);
    state.scanState = details;
    render();
    if (details.status === 'running' || details.status === 'queued' || details.status === 'started') {
      setTimeout(() => pollScan(scanId), 1000);
    }
  } catch (error) {
    console.error(error);
  }
}

function renderScanView() {
  const scan = state.scanState || { id: state.lastScanId, status: 'running', progress: { done: 0, total: 10 }, findings: [] };
  const nodes = [
    'Prepare', 'Core records', 'Nameservers', 'Email', 'DNSSEC', 'Passive subdomains', 'Active probing', 'Enrichment', 'Analysis', 'Report'
  ].map((name, index) => {
    const classes = ['pipeline-node', 'waiting'];
    const item = el('div', { className: classes.join(' ') }, [el('span', { text: name })]);
    if (index < (scan.progress?.done || 0)) item.classList.add('done');
    if (index === (scan.progress?.done || 0) && scan.status === 'running') item.classList.add('running');
    return item;
  });

  const fill = Math.min(100, ((scan.progress?.done || 0) / Math.max(1, scan.progress?.total || 10)) * 100);

  const status = el('div', { className: 'form-card' }, [
    el('div', { className: 'sonar-wrap' }, [
      el('div', { className: 'sonar' }, [
        el('div', { className: 'sonar-label', text: scan.target?.hostname || 'target' })
      ])
    ]),
    el('div', { className: 'pipeline' }, nodes),
    el('div', { className: 'progress-strip' }, [
      el('div', { className: 'progress-bar' }, [el('div', { className: 'progress-fill', attrs: { style: `--p:${fill}%` } })]),
      el('div', { className: 'small-muted', text: `${scan.progress?.done || 0}/${scan.progress?.total || 10} - ${scan.status || 'running'}` })
    ]),
    el('div', { className: 'console' }, [
      el('div', { className: 'console-header' }, [
        el('span', { text: 'live console' }),
        el('button', { className: 'small-btn', text: 'pause' })
      ]),
      el('div', { className: 'console-list' }, (scan.recent_commands || []).map((cmd) => el('div', { className: 'console-entry' }, [
        el('strong', { text: '$ ' }),
        el('span', { text: `${cmd.command_line || 'command'} (${cmd.duration_ms || 0} ms)` })
      ])))
    ]),
    el('div', { className: 'flag-strip' }, [
      el('div', { className: 'flag-pill red', text: `red ${scan.flag_counts?.red ?? 0}` }),
      el('div', { className: 'flag-pill yellow', text: `yellow ${scan.flag_counts?.yellow ?? 0}` }),
      el('div', { className: 'flag-pill green', text: `green ${scan.flag_counts?.green ?? 0}` }),
      el('div', { className: 'flag-pill grey', text: `grey ${scan.flag_counts?.grey ?? 0}` })
    ]),
    el('button', { className: 'secondary-btn', text: 'Cancel scan' })
  ]);
  return status;
}

function downloadExport(format) {
  const scanId = state.lastScanId || state.scanState?.id;
  if (!scanId) return;
  const url = `/api/scans/${encodeURIComponent(scanId)}/export?format=${encodeURIComponent(format)}`;
  const link = document.createElement('a');
  link.href = url;
  link.target = '_blank';
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function renderReport() {
  const scan = state.scanState || { id: state.lastScanId, findings: [], data: {}, target: { hostname: 'example.com' } };
  const findings = scan.findings || [];
  const list = el('div', { className: 'finding-list' }, findings.map((finding) => {
    const color = finding.flag === 'red' ? 'var(--red)' : finding.flag === 'yellow' ? 'var(--yellow)' : finding.flag === 'green' ? 'var(--green)' : 'var(--grey)';
    return el('div', { className: 'finding-card', attrs: { style: `--flag-color:${color}` } }, [
      el('div', { className: 'finding-head' }, [
        el('span', { className: 'dot ' + finding.flag, attrs: { title: finding.flag } }),
        el('span', { className: 'finding-id', text: finding.id }),
        el('span', { className: 'finding-title', text: finding.title })
      ]),
      el('div', { className: 'finding-meta', text: finding.why || 'No explanation available.' }),
      el('div', { className: 'finding-evidence' }, [
        el('div', { className: 'small-muted', text: 'Evidence:' }),
        el('div', { text: (finding.evidence || []).join(', ') || 'No evidence recorded.' })
      ])
    ]);
  }));

  const report = el('div', { className: 'form-card' }, [
    el('div', { className: 'report-header' }, [
      el('div', { className: 'report-meta' }, [
        el('h2', { className: 'report-title', text: scan.target?.hostname || scan.id }),
        el('div', { text: `${scan.status || 'done'} • ${scan.created_at || 'n/a'}` })
      ]),
      el('div', { className: 'tabs' }, [
        el('button', { className: 'tab-btn active', text: 'Findings' }),
        el('button', { className: 'tab-btn', text: 'Records' }),
        el('button', { className: 'tab-btn', text: 'DNSSEC' }),
        el('button', { className: 'small-btn export-btn', text: 'JSON' }),
        el('button', { className: 'small-btn export-btn', text: 'Markdown' }),
        el('button', { className: 'small-btn export-btn', text: 'HTML' })
      ])
    ]),
    el('div', { className: 'summary-row' }, [
      el('div', { className: 'summary-box' }, [el('div', { className: 'label', text: 'nameservers' }), el('div', { className: 'value', text: 'n/a' })]),
      el('div', { className: 'summary-box' }, [el('div', { className: 'label', text: 'DNSSEC' }), el('div', { className: 'value', text: 'n/a' })]),
      el('div', { className: 'summary-box' }, [el('div', { className: 'label', text: 'subdomains' }), el('div', { className: 'value', text: '0' })]),
      el('div', { className: 'summary-box' }, [el('div', { className: 'label', text: 'mail provider' }), el('div', { className: 'value', text: 'n/a' })])
    ]),
    list
  ]);

  report.querySelectorAll('.export-btn').forEach((button) => {
    const format = button.textContent.trim().toLowerCase();
    button.addEventListener('click', () => downloadExport(format === 'markdown' ? 'md' : format));
  });

  return report;
}

function render() {
  if (state.activeView === 'terms') {
    const shell = el('div', { className: 'app-shell center-shell' }, [
      renderTermsView()
    ]);
    appEl.innerHTML = '';
    appEl.appendChild(shell);
    return;
  }

  const mainView = state.activeView === 'scan' ? renderScanView() : state.activeView === 'report' ? renderReport() : renderHome();
  const shell = el('div', { className: 'app-shell' }, [
    el('header', { className: 'topbar' }, [
      el('div', { className: 'brand', text: 'ReconDeck' }, [el('span', { className: 'mark', text: '▌' })]),
      el('div', { className: 'tools' }, [
        el('span', { className: 'tool-pill', text: 'dig ✓' }),
        el('span', { className: 'tool-pill', text: 'whois ✓' })
      ])
    ]),
    el('div', { className: 'layout' }, [
      el('aside', { className: 'sidebar' }, [
        el('h3', { text: 'Past scans' }),
        renderScanList()
      ]),
      el('main', { className: 'main-panel' }, [mainView])
    ])
  ]);
  appEl.innerHTML = '';
  appEl.appendChild(shell);
}

(async () => {
  try {
    const acceptedVersion = localStorage.getItem(TERMS_STORAGE_KEY);
    if (acceptedVersion !== String(TERMS_VERSION)) {
      state.activeView = 'terms';
      try {
        await fetchTermsText();
      } catch (error) {
        console.error(error);
        state.termsText = 'ReconDeck Terms of Use\n\nThis app is for authorized testing only.';
      }
    }
    await loadScans();
    render();
  } catch (error) {
    console.error(error);
    render();
  }
})();
