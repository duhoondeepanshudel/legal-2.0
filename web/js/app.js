/* ═══════════════════════════════════════════════════════════
   Nyaya Graph — Main Application JavaScript
   Premium Interactive Legal Analytics & Knowledge Graph
   ═══════════════════════════════════════════════════════════ */

const API = '/api';
let graphData = null;
let graphSim = null;

// Criminal Law Reforms Concordance Database (IPC ⇆ BNS, CrPC ⇆ BNSS, IEA ⇆ BSA)
const CONCORDANCE_DATA = {
    IPC: {
        "302": { newSection: "103", title: "Murder", desc: "Punishment for murder. Penalty remains death or imprisonment for life, and fine." },
        "307": { newSection: "109", title: "Attempt to Murder", desc: "Attempt to murder. Imprisonment up to 10 years and fine; if hurt is caused, up to life imprisonment." },
        "120B": { newSection: "61", title: "Criminal Conspiracy", desc: "Punishment of criminal conspiracy." },
        "375": { newSection: "63", title: "Rape Definition", desc: "Rape defined with updated gender-neutral terms for victims and child-specific protections." },
        "376": { newSection: "64", title: "Punishment for Rape", desc: "Punishment for rape. Minimum sentence increased from 7 to 10 years, up to life imprisonment." },
        "498A": { newSection: "85", title: "Cruelty by Husband or Relatives", desc: "Husband or relative of husband of a woman subjecting her to cruelty. Imprisonment up to 3 years." },
        "420": { newSection: "318", title: "Cheating", desc: "Cheating and dishonestly inducing delivery of property. Imprisonment up to 7 years and fine." },
        "304B": { newSection: "80", title: "Dowry Death", desc: "Dowry death. Punishment remains imprisonment for not less than 7 years, up to life." },
        "124A": { newSection: "152", title: "Sedition (now Act endangering Sovereignty)", desc: "Sedition is repealed. Replaced by acts endangering sovereignty, unity, and integrity of India." },
        "379": { newSection: "303", title: "Theft", desc: "Punishment for simple theft. Imprisonment up to 3 years, or fine, or community service (new addition)." },
        "506": { newSection: "351", title: "Criminal Intimidation", desc: "Punishment for criminal intimidation. Imprisonment up to 2 years, or fine, or both." }
    },
    CrPC: {
        "438": { newSection: "482", title: "Anticipatory Bail", desc: "Direction for grant of bail to person apprehending arrest. Retains structure of anticipatory bail." },
        "482": { newSection: "528", title: "Inherent Powers of High Court", desc: "Saving of inherent powers of High Court to prevent abuse of process or secure justice." },
        "125": { newSection: "144", title: "Maintenance of Wife, Children, Parents", desc: "Order for maintenance of wives, children, and parents. Simplifies and speeds up claims." },
        "154": { newSection: "173", title: "First Information Report (FIR)", desc: "Information in cognizable cases. Introduces 'Zero FIR' (can be filed at any police station) and e-FIR." },
        "161": { newSection: "180", title: "Examination of Witnesses", desc: "Examination of witnesses by police. Allows audio-video recording of statements." },
        "167": { newSection: "187", title: "Remand & Police Custody", desc: "Procedure when investigation cannot be completed in 24 hours. Allows 15 days of police custody spread over 60/90 days." },
        "173": { newSection: "193", title: "Police Report (Chargesheet)", desc: "Report of investigation by police officer. Chargesheet must be filed within 90 days, extensions up to 180 days." }
    },
    IEA: {
        "32": { newSection: "26", title: "Dying Declaration", desc: "Cases in which statement of relevant fact by person who is dead or cannot be found is relevant." },
        "25": { newSection: "23", title: "Confession to Police", desc: "Confession to police officer not to be proved against an accused person." },
        "27": { newSection: "23(2)", title: "Fact Discovered in Custody", desc: "How much of information received from accused may be proved (discovery of fact)." },
        "45": { newSection: "39", title: "Opinion of Experts", desc: "Opinions of experts. Expanded to explicitly include digital and cyber-forensic experts." },
        "65B": { newSection: "63", title: "Admissibility of Electronic Records", desc: "Special provisions as to admissibility of electronic records. Updated to encompass cloud, server, and handheld devices." }
    }
};

// Modal navigation history stack
let modalHistoryStack = [];
let modalHistoryIndex = -1;

// ─── Initialization ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initTabs();
    initSearch();
    initModal();
    initConcordanceTool();
    loadDashboard();
    
    // Auto-render Lucide icons
    lucide.createIcons();
});

// ─── Theme Management ────────────────────────────────────
function initTheme() {
    const toggleBtn = document.getElementById('theme-toggle');
    let theme = localStorage.getItem('theme') || 'dark';
    
    document.documentElement.setAttribute('data-theme', theme);
    
    toggleBtn.addEventListener('click', () => {
        theme = theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        // Re-draw graph to update coordinate background and texts if open
        if (nodes.length > 0) {
            draw();
        }
    });
}

// ─── Tab Navigation ──────────────────────────────────────
function initTabs() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`section-${target}`).classList.add('active');
            
            if (target === 'cases') loadCases(1);
            if (target === 'graph') loadGraph();
            if (target === 'landmarks') loadLandmarks();
            if (target === 'judges') loadJudges();
            if (target === 'statutes') loadStatutes();
        });
    });
}

// ─── Search ──────────────────────────────────────────────
function initSearch() {
    const input = document.getElementById('global-search');
    const dropdown = document.getElementById('search-results');
    let debounce = null;

    input.addEventListener('input', () => {
        clearTimeout(debounce);
        const q = input.value.trim();
        if (q.length < 2) { dropdown.classList.remove('active'); return; }
        debounce = setTimeout(async () => {
            try {
                const res = await fetch(`${API}/search?q=${encodeURIComponent(q)}&limit=15`);
                const data = await res.json();
                renderSearchResults(data, dropdown);
            } catch(e) { console.error(e); }
        }, 300);
    });

    input.addEventListener('blur', () => setTimeout(() => dropdown.classList.remove('active'), 200));
    input.addEventListener('focus', () => { if (input.value.trim().length >= 2) dropdown.classList.add('active'); });
}

function renderSearchResults(results, dropdown) {
    if (!results.length) { dropdown.classList.remove('active'); return; }
    dropdown.innerHTML = results.map(r => `
        <div class="search-item" data-id="${r.id}" data-type="${r.type}" data-label="${r.label.replace(/"/g, '&quot;')}">
            <span class="search-item-type type-${r.type}">${r.type}</span>
            <span class="search-item-name">${r.label}</span>
        </div>
    `).join('');
    dropdown.classList.add('active');
    
    dropdown.querySelectorAll('.search-item').forEach(item => {
        item.addEventListener('click', () => {
            const id = item.dataset.id;
            const type = item.dataset.type;
            const label = item.dataset.label;
            dropdown.classList.remove('active');
            input.value = '';
            
            if (type === 'Case') {
                showCaseModal(id);
            } else if (type === 'Judge') {
                document.getElementById('tab-judges').click();
                setTimeout(() => {
                    showJudgeModal(encodeURIComponent(label), label, '—');
                }, 300);
            } else if (type === 'Statute') {
                document.getElementById('tab-statutes').click();
                setTimeout(() => {
                    showStatuteModal(encodeURIComponent(label), label, '—');
                }, 300);
            }
        });
    });
}

// ─── Modal & History Stack ──────────────────────────────
function initModal() {
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('modal-backdrop').addEventListener('click', closeModal);
    
    // Wire history navigation buttons
    document.getElementById('modal-nav-back').addEventListener('click', modalGoBack);
    document.getElementById('modal-nav-forward').addEventListener('click', modalGoForward);
}

function closeModal() {
    document.getElementById('case-modal').classList.add('hidden');
    modalHistoryStack = [];
    modalHistoryIndex = -1;
}

function updateModalNavButtons() {
    const backBtn = document.getElementById('modal-nav-back');
    const fwdBtn = document.getElementById('modal-nav-forward');
    
    backBtn.disabled = modalHistoryIndex <= 0;
    fwdBtn.disabled = modalHistoryIndex >= modalHistoryStack.length - 1;
}

async function showCaseModal(caseId) {
    // Check if we are opening a new branch or continuing
    if (modalHistoryIndex === -1 || modalHistoryStack[modalHistoryIndex] !== caseId) {
        // Truncate any forward history if we were in the middle of backtracking
        if (modalHistoryIndex < modalHistoryStack.length - 1) {
            modalHistoryStack = modalHistoryStack.slice(0, modalHistoryIndex + 1);
        }
        modalHistoryStack.push(caseId);
        modalHistoryIndex = modalHistoryStack.length - 1;
    }
    
    updateModalNavButtons();
    loadCaseDetails(caseId);
}

function modalGoBack() {
    if (modalHistoryIndex > 0) {
        modalHistoryIndex--;
        updateModalNavButtons();
        loadCaseDetails(modalHistoryStack[modalHistoryIndex]);
    }
}

function modalGoForward() {
    if (modalHistoryIndex < modalHistoryStack.length - 1) {
        modalHistoryIndex++;
        updateModalNavButtons();
        loadCaseDetails(modalHistoryStack[modalHistoryIndex]);
    }
}

// Global hook for hyperlinks inside the modal judgment text
window.openCaseFromModal = function(caseId) {
    showCaseModal(caseId);
};

window.openStatuteFromModal = function(statuteName) {
    closeModal();
    document.getElementById('tab-statutes').click();
    setTimeout(() => {
        showStatuteModal(encodeURIComponent(statuteName), statuteName, '—');
    }, 450);
};

async function loadCaseDetails(caseId) {
    const modal = document.getElementById('case-modal');
    const body = document.getElementById('modal-body');
    const copyBtn = document.getElementById('modal-action-copy');
    
    body.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:4rem;"><i data-lucide="loader-2" class="animate-spin" style="width:36px;height:36px;margin:0 auto 1rem;"></i>Loading case intelligence records...</p>';
    modal.classList.remove('hidden');
    lucide.createIcons();

    try {
        const res = await fetch(`${API}/case/${caseId}`);
        const data = await res.json();
        if (data.error) { body.innerHTML = `<p style="color:var(--accent-rose);text-align:center;padding:2rem;">${data.error}</p>`; return; }
        
        const c = data.case;
        const p = c.properties || {};
        const judgmentId = `judgment-full-${caseId}`;
        
        // Share action configuration
        copyBtn.onclick = () => {
            const shareText = `Nyaya Graph Case Record: ${c.label} (${p.year}) - Court: ${p.court}. View on Nyaya Graph.`;
            navigator.clipboard.writeText(shareText);
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i data-lucide="check"></i> Copied!';
            lucide.createIcons();
            setTimeout(() => {
                copyBtn.innerHTML = originalText;
                lucide.createIcons();
            }, 1500);
        };

        // Check for BNS criminal law transition alert
        let bnsAlertHtml = '';
        if (data.statutes && data.statutes.length) {
            const reformMappings = [];
            data.statutes.forEach(s => {
                const sname = s.name.toUpperCase();
                const m = sname.match(/SECTION\s+(\d+[A-Z]*)\s+OF\s+(?:THE\s+)?(INDIAN PENAL CODE|CODE OF CRIMINAL PROCEDURE|EVIDENCE ACT)/);
                if (m) {
                    const sec = m[1];
                    const actAbbr = m[2].includes("PENAL") ? "IPC" : (m[2].includes("PROCEDURE") ? "CrPC" : "IEA");
                    const lookup = CONCORDANCE_DATA[actAbbr][sec];
                    if (lookup) {
                        reformMappings.push({
                            old: `Sec ${sec} ${actAbbr}`,
                            new: `Sec ${lookup.newSection} ${actAbbr === 'IPC' ? 'BNS' : (actAbbr === 'CrPC' ? 'BNSS' : 'BSA')}`,
                            title: lookup.title
                        });
                    }
                }
            });
            
            if (reformMappings.length > 0) {
                bnsAlertHtml = `
                    <div class="modal-statute-reform-alert">
                        <div class="alert-header">
                            <i data-lucide="alert-triangle"></i> Criminal Law Reform Alert (July 2024 Transition)
                        </div>
                        <div class="alert-body">
                            This judgment references provisions from historical acts. Under the 2023 penal reforms:
                            <ul style="margin: 0.4rem 0 0 1.25rem; padding: 0;">
                                ${reformMappings.map(rm => `<li><strong>${rm.old}</strong> (${rm.title}) maps to <strong>${rm.new}</strong></li>`).join('')}
                            </ul>
                        </div>
                    </div>
                `;
            }
        }

        // Hyperlink parser for judgment summaries
        let summaryHtml = data.summary || "No summary available.";
        let fullTextHtml = data.judgment_text ? escapeHtml(data.judgment_text) : "";

        // Hyperlink matching precedents
        if (data.precedents_cited && data.precedents_cited.length) {
            data.precedents_cited.forEach(pc => {
                if (pc.name && pc.name.length > 5) {
                    const escName = escapeHtml(pc.name);
                    const linkMarkup = `<span class="legal-link" onclick="openCaseFromModal('${pc.id}')">${escName}</span>`;
                    
                    // Replace safe regex
                    try {
                        const regex = new RegExp(escapeRegExp(escName), 'gi');
                        summaryHtml = summaryHtml.replace(regex, linkMarkup);
                        if (fullTextHtml) {
                            fullTextHtml = fullTextHtml.replace(regex, linkMarkup);
                        }
                    } catch(err) {}
                }
            });
        }

        // Hyperlink matching statutes
        if (data.statutes && data.statutes.length) {
            data.statutes.forEach(s => {
                if (s.name && s.name.length > 3) {
                    const escName = escapeHtml(s.name);
                    const linkMarkup = `<span class="legal-link" onclick="openStatuteFromModal('${escName}')">${escName}</span>`;
                    try {
                        const regex = new RegExp(escapeRegExp(escName), 'gi');
                        summaryHtml = summaryHtml.replace(regex, linkMarkup);
                        if (fullTextHtml) {
                            fullTextHtml = fullTextHtml.replace(regex, linkMarkup);
                        }
                    } catch(err) {}
                }
            });
        }

        body.innerHTML = `
            <div class="modal-case-name">${c.label}</div>
            <div class="modal-meta">
                <span class="modal-meta-item"><i data-lucide="calendar"></i> ${p.year || 'N/A'}</span>
                <span class="modal-meta-item"><i data-lucide="building"></i> ${p.court || 'N/A'}</span>
                <span class="modal-meta-item"><i data-lucide="tag"></i> ${p.case_type || 'N/A'}</span>
            </div>
            
            ${bnsAlertHtml}
            
            <div class="modal-section">
                <h3><i data-lucide="file-text"></i> Judgment Analysis & Summary</h3>
                <div class="judgment-summary-box">
                    <div class="judgment-summary-text">${summaryHtml}</div>
                </div>
                ${data.judgment_text ? `
                <div class="judgment-full-text-container">
                    <button class="toggle-judgment-btn" onclick="const pNode = this.parentNode.querySelector('.judgment-full-text'); pNode.classList.toggle('hidden'); this.innerHTML = pNode.classList.contains('hidden') ? '<i data-lucide=\\'chevrons-down-up\\'></i> Show Full Judgment Text' : '<i data-lucide=\\'chevrons-up-down\\'></i> Hide Full Judgment Text'; lucide.createIcons();">
                        <i data-lucide="chevrons-down-up"></i> Show Full Judgment Text
                    </button>
                    <div class="judgment-full-text hidden">
                        ${fullTextHtml}
                        <button class="btn-scroll-top" onclick="this.parentNode.scrollTop = 0;" title="Scroll to Top"><i data-lucide="arrow-up"></i></button>
                    </div>
                </div>
                ` : ''}
            </div>
            
            ${data.judges && data.judges.length ? `
            <div class="modal-section">
                <h3><i data-lucide="users"></i> Judicial Bench</h3>
                <ul class="modal-list">${data.judges.map(j => `
                    <li onclick="closeModal(); document.getElementById('tab-judges').click(); setTimeout(() => { showJudgeModal('${encodeURIComponent(j.name)}', '${j.name.replace(/'/g, "\\'")}', '—'); }, 400);">${j.name}</li>
                `).join('')}</ul>
            </div>` : ''}
            
            ${data.precedents_cited && data.precedents_cited.length ? `
            <div class="modal-section">
                <h3><i data-lucide="book-open"></i> Precedents Cited (${data.precedents_cited.length})</h3>
                <ul class="modal-list">${data.precedents_cited.map(pc => `
                    <li onclick="openCaseFromModal('${pc.id}')">${pc.name}</li>
                `).join('')}</ul>
            </div>` : ''}
            
            ${data.cited_by && data.cited_by.length ? `
            <div class="modal-section">
                <h3><i data-lucide="link"></i> Cited By (${data.cited_by.length})</h3>
                <ul class="modal-list">${data.cited_by.map(cb => `
                    <li onclick="openCaseFromModal('${cb.id}')">${cb.name}</li>
                `).join('')}</ul>
            </div>` : ''}
            
            ${data.statutes && data.statutes.length ? `
            <div class="modal-section">
                <h3><i data-lucide="bookmark"></i> Statutes Referenced (${data.statutes.length})</h3>
                <ul class="modal-list">${data.statutes.map(s => `
                    <li onclick="openStatuteFromModal('${s.name}')">${s.name}</li>
                `).join('')}</ul>
            </div>` : ''}
        `;
        
        lucide.createIcons();
        
    } catch(e) {
        console.error("Error rendering modal details:", e);
        body.innerHTML = `<p style="color:var(--accent-rose);text-align:center;padding:2rem;">Error loading case intelligence records.</p>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
}

// ─── Dashboard Tab Analytics ──────────────────────────────
async function loadDashboard() {
    const loading = document.getElementById('loading-screen');
    try {
        document.getElementById('loading-text').textContent = 'Loading graph intelligence indicators...';
        const [stats, landmarks, judges, statutes, courts, years] = await Promise.all([
            fetch(`${API}/stats`).then(r => r.json()),
            fetch(`${API}/landmarks?limit=8`).then(r => r.json()),
            fetch(`${API}/judges?limit=8`).then(r => r.json()),
            fetch(`${API}/statutes?limit=8`).then(r => r.json()),
            fetch(`${API}/courts`).then(r => r.json()),
            fetch(`${API}/years`).then(r => r.json())
        ]);

        // Stats Counters
        animateCounter('stat-cases-val', stats.case_nodes || 0);
        animateCounter('stat-judges-val', stats.judge_nodes || 0);
        animateCounter('stat-statutes-val', stats.statute_nodes || 0);
        animateCounter('stat-citations-val', stats.cites_edges || 0);
        animateCounter('stat-edges-val', stats.total_edges || 0);
        animateCounter('stat-nodes-val', stats.total_nodes || 0);

        // Update cases total count dynamic placeholder
        const dynamicCountEl = document.getElementById('cases-total-count');
        if (dynamicCountEl) {
            dynamicCountEl.textContent = (stats.case_nodes || 0).toLocaleString();
        }

        // Landmark cases preview list
        document.getElementById('landmarks-preview').innerHTML = landmarks.map(l => `
            <div class="mini-item" onclick="showCaseModal('${l.case_id}')">
                <span class="mini-name">${l.case_name}</span>
                <span class="mini-badge badge-citations">${l.citations} citations</span>
            </div>
        `).join('');

        // Judge preview list
        document.getElementById('judges-preview').innerHTML = judges.map(j => `
            <div class="mini-item" onclick="document.getElementById('tab-judges').click(); setTimeout(() => { showJudgeModal('${encodeURIComponent(j.judge_name)}', '${j.judge_name.replace(/'/g, "\\'")}', ${j.cases_decided}); }, 300);">
                <span class="mini-name">${j.judge_name}</span>
                <span class="mini-badge badge-cases">${j.cases_decided} cases</span>
            </div>
        `).join('');

        // Statute preview list
        document.getElementById('statutes-preview').innerHTML = statutes.map(s => {
            const hasBns = isOldCriminalLaw(s.statute_name);
            return `
                <div class="mini-item" onclick="document.getElementById('tab-statutes').click(); setTimeout(() => { showStatuteModal('${encodeURIComponent(s.statute_name)}', '${s.statute_name.replace(/'/g, "\\'")}', ${s.references}); }, 300);">
                    <span class="mini-name">${s.statute_name}</span>
                    <span class="mini-badge badge-refs" style="${hasBns ? 'background:rgba(251,191,36,0.15);color:var(--accent-amber);' : ''}">
                        ${s.references} refs ${hasBns ? '⚠️' : ''}
                    </span>
                </div>
            `;
        }).join('');

        // Render Premium SVG Court distribution chart
        renderCourtChartSVG(courts);

        // Render Premium SVG Decades trend line chart
        renderYearChartSVG(years);

    } catch(e) {
        console.error('Dashboard load error:', e);
        document.getElementById('loading-text').innerHTML = '<span style="color:var(--accent-rose)">Error connecting to Nyaya API.</span><br><br>Please verify the Flask server is running locally (e.g. <code>python api/server.py</code>).';
        return;
    }
    setTimeout(() => {
        loading.classList.add('hidden');
        lucide.createIcons();
    }, 600);
}

function animateCounter(elemId, target) {
    const el = document.getElementById(elemId);
    let current = 0;
    const step = Math.ceil(target / 30);
    const interval = setInterval(() => {
        current += step;
        if (current >= target) { current = target; clearInterval(interval); }
        el.textContent = current.toLocaleString();
    }, 25);
}

function isOldCriminalLaw(statuteName) {
    const name = statuteName.toUpperCase();
    return name.includes("PENAL CODE") || name.includes("CRIMINAL PROCEDURE") || name.includes("EVIDENCE ACT");
}

// ─── SVG Chart Construction ──────────────────────────────
function renderCourtChartSVG(data) {
    const container = document.getElementById('court-chart');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Sort and limit to top 6 courts
    const topData = data.slice(0, 6);
    const maxVal = Math.max(...topData.map(d => d.cases)) || 1;
    
    const margin = { top: 20, right: 20, bottom: 40, left: 160 };
    const chartW = width - margin.left - margin.right;
    const chartH = height - margin.top - margin.bottom;
    
    let svgHtml = `<svg class="chart-svg" viewBox="0 0 ${width} ${height}">`;
    
    // Gradients definition
    svgHtml += `
        <defs>
            <linearGradient id="barGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="var(--accent-primary)" />
                <stop offset="100%" stop-color="var(--accent-secondary)" />
            </linearGradient>
        </defs>
    `;
    
    // Draw Y axis labels and bars
    const barHeight = chartH / topData.length;
    topData.forEach((d, idx) => {
        const y = margin.top + idx * barHeight + (barHeight * 0.15);
        const activeBarH = barHeight * 0.7;
        const barW = (d.cases / maxVal) * chartW;
        
        const shortName = d.court.replace('High Court', 'HC').replace('Supreme Court of India', 'Supreme Court');
        
        // Y grid lines
        svgHtml += `<line class="chart-grid-line" x1="${margin.left}" y1="${y + activeBarH/2}" x2="${margin.left + chartW}" y2="${y + activeBarH/2}"></line>`;
        
        // Axis Label
        svgHtml += `
            <text class="chart-label-text" x="${margin.left - 15}" y="${y + activeBarH/2 + 4}" text-anchor="end">
                ${shortName}
            </text>
        `;
        
        // Bar Rectangle with click trigger to filter Cases tab
        svgHtml += `
            <rect class="chart-bar-rect" x="${margin.left}" y="${y}" width="${barW}" height="${activeBarH}" 
                  fill="url(#barGrad)" data-court="${d.court.replace(/"/g, '&quot;')}"
                  onclick="window.filterByCourtFromChart('${d.court.replace(/'/g, "\\'")}')">
                <title>${d.court}: ${d.cases} cases</title>
            </rect>
        `;
        
        // Value Text
        svgHtml += `
            <text class="chart-value-text" x="${margin.left + barW + 15}" y="${y + activeBarH/2 + 4}" text-anchor="start" fill="var(--text-primary)">
                ${d.cases}
            </text>
        `;
    });
    
    // Draw vertical base axis line
    svgHtml += `<line class="chart-axis-line" x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${margin.top + chartH}"></line>`;
    
    svgHtml += `</svg>`;
    container.innerHTML = svgHtml;
}

window.filterByCourtFromChart = function(courtName) {
    document.getElementById('tab-cases').click();
    document.getElementById('cases-court-filter').value = courtName;
    loadCases(1);
};

function renderYearChartSVG(data) {
    const container = document.getElementById('year-chart');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Group and sort data (Timeline)
    const sortedData = data.filter(d => d.year > 1940).sort((a, b) => a.year - b.year);
    if (!sortedData.length) return;
    
    const maxVal = Math.max(...sortedData.map(d => d.cases)) || 1;
    
    const margin = { top: 30, right: 30, bottom: 40, left: 50 };
    const chartW = width - margin.left - margin.right;
    const chartH = height - margin.top - margin.bottom;
    
    const stepX = chartW / (sortedData.length - 1 || 1);
    
    let svgHtml = `<svg class="chart-svg" viewBox="0 0 ${width} ${height}">`;
    
    // Gradients
    svgHtml += `
        <defs>
            <linearGradient id="areaGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="var(--accent-cyan)" stop-opacity="0.3" />
                <stop offset="100%" stop-color="var(--accent-cyan)" stop-opacity="0.0" />
            </linearGradient>
            <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="var(--accent-primary)" />
                <stop offset="50%" stop-color="var(--accent-cyan)" />
                <stop offset="100%" stop-color="var(--accent-emerald)" />
            </linearGradient>
        </defs>
    `;
    
    // Build line coordinates path
    let points = [];
    sortedData.forEach((d, idx) => {
        const x = margin.left + idx * stepX;
        const y = margin.top + chartH - (d.cases / maxVal) * chartH;
        points.push({ x, y, data: d });
    });
    
    // Draw grid horizontal line segments
    const gridRows = 4;
    for (let i = 0; i <= gridRows; i++) {
        const y = margin.top + (i / gridRows) * chartH;
        const val = Math.round(maxVal - (i / gridRows) * maxVal);
        svgHtml += `
            <line class="chart-grid-line" x1="${margin.left}" y1="${y}" x2="${margin.left + chartW}" y2="${y}"></line>
            <text class="chart-label-text" x="${margin.left - 10}" y="${y + 3}" text-anchor="end">${val}</text>
        `;
    }
    
    // Area path
    let areaPathD = `M ${points[0].x} ${margin.top + chartH} `;
    points.forEach(p => {
        areaPathD += `L ${p.x} ${p.y} `;
    });
    areaPathD += `L ${points[points.length-1].x} ${margin.top + chartH} Z`;
    svgHtml += `<path class="chart-area-path" d="${areaPathD}"></path>`;
    
    // Line path
    let linePathD = `M ${points[0].x} ${points[0].y} `;
    for (let i = 1; i < points.length; i++) {
        linePathD += `L ${points[i].x} ${points[i].y} `;
    }
    svgHtml += `<path class="chart-line-path" d="${linePathD}"></path>`;
    
    // Draw dots and X labels
    points.forEach((p, idx) => {
        // Label X for every alternate point
        if (idx % 2 === 0 || idx === points.length - 1) {
            svgHtml += `
                <text class="chart-label-text" x="${p.x}" y="${margin.top + chartH + 20}" text-anchor="middle">
                    ${p.data.year}
                </text>
                <line class="chart-grid-line" x1="${p.x}" y1="${margin.top}" x2="${p.x}" y2="${margin.top + chartH}"></line>
            `;
        }
        
        // Interactive Circle node
        svgHtml += `
            <circle class="chart-dot" cx="${p.x}" cy="${p.y}" r="4.5"
                    onclick="window.filterByYearFromChart(${p.data.year})">
                <title>Year ${p.data.year}: ${p.data.cases} cases</title>
            </circle>
        `;
    });
    
    svgHtml += `</svg>`;
    container.innerHTML = svgHtml;
}

window.filterByYearFromChart = function(year) {
    document.getElementById('tab-cases').click();
    document.getElementById('cases-court-filter').value = '';
    document.getElementById('cases-search').value = '';
    // Use an input hack to query by year on next load
    window.filterYearQuery = year;
    loadCases(1);
};

// ─── Cases Database Tab ──────────────────────────────────
let casesCurrentPage = 1;
let casesCourtListLoaded = false;

async function loadCases(page = 1) {
    casesCurrentPage = page;
    const container = document.getElementById('cases-list');
    const pagination = document.getElementById('cases-pagination');
    const totalEl = document.getElementById('cases-total');

    // Load unique court list for options dropdown once
    if (!casesCourtListLoaded) {
        casesCourtListLoaded = true;
        try {
            const courts = await fetch(`${API}/courts/list`).then(r => r.json());
            const sel = document.getElementById('cases-court-filter');
            courts.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = c.replace(' High Court', ' HC').replace('Supreme Court of India', 'Supreme Court');
                sel.appendChild(opt);
            });
        } catch(e) { console.error(e); }

        // Wire filter events
        let casesDebounce = null;
        document.getElementById('cases-search').addEventListener('input', () => {
            clearTimeout(casesDebounce);
            casesDebounce = setTimeout(() => loadCases(1), 300);
        });
        document.getElementById('cases-court-filter').addEventListener('change', () => loadCases(1));
        document.getElementById('cases-sort').addEventListener('change', () => loadCases(1));
    }

    const q = document.getElementById('cases-search').value.trim();
    const court = document.getElementById('cases-court-filter').value;
    const sort = document.getElementById('cases-sort').value;
    
    // Check for timeline chart click year filter trigger
    let yearQueryParam = "";
    if (window.filterYearQuery) {
        yearQueryParam = `&year=${window.filterYearQuery}`;
        totalEl.innerHTML = `<span style="color:var(--accent-cyan);cursor:pointer;text-decoration:underline;" onclick="window.clearYearFilter()">Clear Year: ${window.filterYearQuery} ✖</span>`;
    }

    container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:4rem;"><i data-lucide="loader" class="animate-spin" style="width:32px;height:32px;margin:0 auto 1rem;"></i>Querying court records database...</p>';
    lucide.createIcons();

    try {
        let url = `${API}/cases?page=${page}&per_page=15&sort=${sort}`;
        if (q) url += `&q=${encodeURIComponent(q)}`;
        if (court) url += `&court=${encodeURIComponent(court)}`;
        if (yearQueryParam) url += yearQueryParam;

        const res = await fetch(url);
        const data = await res.json();

        if (!window.filterYearQuery) {
            totalEl.textContent = `${data.total.toLocaleString()} records matched`;
        } else {
            totalEl.innerHTML = `<span style="color:var(--accent-cyan);cursor:pointer;font-weight:bold;margin-right:1rem;" onclick="window.clearYearFilter()">Year: ${window.filterYearQuery} ✖</span> ${data.total.toLocaleString()} records matched`;
        }

        if (!data.cases.length) {
            container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:4rem;">No judgment records match your search parameters.</p>';
            pagination.innerHTML = '';
            return;
        }

        const startNum = (data.page - 1) * data.per_page;
        container.innerHTML = data.cases.map((c, i) => `
            <div class="case-card" onclick="showCaseModal('${c.case_id}')">
                <div class="case-card-header">
                    <div class="case-card-rank">${startNum + i + 1}</div>
                    <div class="case-card-info">
                        <div class="case-card-name">${c.case_name}</div>
                        <div class="case-card-meta">
                            <span><i data-lucide="calendar" style="width:12px;height:12px;"></i> ${c.year || 'N/A'}</span>
                            <span><i data-lucide="building" style="width:12px;height:12px;"></i> ${(c.court || '').replace('High Court', 'HC').replace('Supreme Court of India', 'SC')}</span>
                            <span><i data-lucide="tag" style="width:12px;height:12px;"></i> ${c.case_type || ''}</span>
                            ${c.judges && c.judges.length ? `<span><i data-lucide="user-check" style="width:12px;height:12px;"></i> ${c.judges[0]}${c.judges.length > 1 ? ` +${c.judges.length - 1}` : ''}</span>` : ''}
                        </div>
                    </div>
                </div>
                <div class="case-card-summary">${c.summary || ''}</div>
            </div>
        `).join('');

        renderPagination(data.page, data.total_pages, data.total);
        lucide.createIcons();

    } catch(e) {
        console.error('Cases load error:', e);
        container.innerHTML = '<p style="color:var(--accent-rose);text-align:center;padding:3rem;">Error establishing database network connection.</p>';
    }
}

window.clearYearFilter = function() {
    window.filterYearQuery = null;
    loadCases(1);
};

function renderPagination(currentPage, totalPages, total) {
    const pagination = document.getElementById('cases-pagination');
    if (totalPages <= 1) { pagination.innerHTML = ''; return; }

    let html = '';
    html += `<button class="page-btn" ${currentPage <= 1 ? 'disabled' : ''} onclick="loadCases(${currentPage - 1})"><i data-lucide="chevron-left" style="width:14px;height:14px;vertical-align:middle;"></i> Prev</button>`;

    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }

    if (startPage > 1) {
        html += `<button class="page-btn" onclick="loadCases(1)">1</button>`;
        if (startPage > 2) html += `<span class="page-info">...</span>`;
    }

    for (let p = startPage; p <= endPage; p++) {
        html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="loadCases(${p})">${p}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += `<span class="page-info">...</span>`;
        html += `<button class="page-btn" onclick="loadCases(${totalPages})">${totalPages}</button>`;
    }

    html += `<button class="page-btn" ${currentPage >= totalPages ? 'disabled' : ''} onclick="loadCases(${currentPage + 1})">Next <i data-lucide="chevron-right" style="width:14px;height:14px;vertical-align:middle;"></i></button>`;
    html += `<span class="page-info">Page ${currentPage} of ${totalPages}</span>`;

    pagination.innerHTML = html;
}

// ─── Landmarks Tab ──────────────────────────────────────
async function loadLandmarks() {
    const container = document.getElementById('landmarks-list');
    if (container.children.length > 0) return;
    container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:4rem;"><i data-lucide="loader" class="animate-spin" style="width:32px;height:32px;margin:0 auto 1rem;"></i>Sorting landmark citations...</p>';
    lucide.createIcons();
    
    try {
        const data = await fetch(`${API}/landmarks?limit=50`).then(r => r.json());
        container.innerHTML = data.map((l, i) => `
            <div class="data-item" onclick="showCaseModal('${l.case_id}')">
                <div class="data-rank">#${i + 1}</div>
                <div class="data-info">
                    <div class="data-name">${l.case_name}</div>
                    <div class="data-meta">${l.court || ''} · ${l.year || ''}</div>
                </div>
                <div class="data-badge badge-citations"><i data-lucide="link" style="width:12px;height:12px;"></i> ${l.citations} citations</div>
            </div>
        `).join('');
        lucide.createIcons();
    } catch(e) { container.innerHTML = '<p style="color:var(--accent-rose)">Error connecting to server.</p>'; }
}

// ─── Judges Tab ──────────────────────────────────────────
async function loadJudges() {
    const container = document.getElementById('judges-list');
    container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:4rem;"><i data-lucide="loader" class="animate-spin" style="width:32px;height:32px;margin:0 auto 1rem;"></i>Compiling judicial decisions record...</p>';
    lucide.createIcons();
    
    try {
        const data = await fetch(`${API}/judges?limit=50`).then(r => r.json());
        container.innerHTML = data.map((j, i) => `
            <div class="data-item" onclick="showJudgeModal('${encodeURIComponent(j.judge_name)}', '${j.judge_name.replace(/'/g, "\\'")}', ${j.cases_decided})">
                <div class="data-rank">#${i + 1}</div>
                <div class="data-info">
                    <div class="data-name">${j.judge_name}</div>
                </div>
                <div class="data-badge badge-cases"><i data-lucide="scale" style="width:12px;height:12px;"></i> ${j.cases_decided} cases</div>
            </div>
        `).join('');
        lucide.createIcons();
    } catch(e) { container.innerHTML = '<p style="color:var(--accent-rose)">Error connecting to server.</p>'; }
}

async function showJudgeModal(encodedName, displayName, totalCases) {
    const modal = document.getElementById('case-modal');
    const body = document.getElementById('modal-body');
    body.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:4rem;"><i data-lucide="loader" class="animate-spin" style="width:32px;height:32px;margin:0 auto 1rem;"></i>Retrieving cases for bench...</p>';
    modal.classList.remove('hidden');
    lucide.createIcons();
    
    try {
        const res = await fetch(`${API}/judge/${encodedName}/cases`);
        const cases = await res.json();
        body.innerHTML = `
            <div class="modal-case-name">👨‍⚖️ Justice ${displayName}</div>
            <div class="modal-meta">
                <span class="modal-meta-item"><i data-lucide="scale"></i> ${totalCases} cases decided</span>
            </div>
            <div class="modal-section">
                <h3>📁 Caseload Portfolio (${cases.length})</h3>
                ${cases.length ? `
                <ul class="modal-list">${cases.map(c => `
                    <li onclick="openCaseFromModal('${c.case_id}')">${c.case_name} <span style='color:var(--text-muted);font-size:0.75rem;'>${c.court || ''} · ${c.year || ''}</span></li>
                `).join('')}</ul>` : '<p style="color:var(--text-muted)">No cases indexed for this judge.</p>'}
            </div>
        `;
        lucide.createIcons();
    } catch(e) {
        body.innerHTML = '<p style="color:var(--accent-rose);">Error loading judge caseload records.</p>';
    }
}

// ─── Statutes Tab ──────────────────────────────────────
async function loadStatutes() {
    const container = document.getElementById('statutes-list');
    container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:4rem;"><i data-lucide="loader" class="animate-spin" style="width:32px;height:32px;margin:0 auto 1rem;"></i>Calculating statute references...</p>';
    lucide.createIcons();
    
    try {
        const data = await fetch(`${API}/statutes?limit=50`).then(r => r.json());
        container.innerHTML = data.map((s, i) => {
            const hasBns = isOldCriminalLaw(s.statute_name);
            return `
                <div class="data-item" onclick="showStatuteModal('${encodeURIComponent(s.statute_name)}', '${s.statute_name.replace(/'/g, "\\'")}', ${s.references})">
                    <div class="data-rank">#${i + 1}</div>
                    <div class="data-info">
                        <div class="data-name">${s.statute_name}</div>
                    </div>
                    <div class="data-badge badge-refs" style="${hasBns ? 'background:rgba(251,191,36,0.15);color:var(--accent-amber);' : ''}">
                        <i data-lucide="book-open" style="width:12px;height:12px;"></i> ${s.references} refs ${hasBns ? '⚠️' : ''}
                    </div>
                </div>
            `;
        }).join('');
        lucide.createIcons();
    } catch(e) { container.innerHTML = '<p style="color:var(--accent-rose)">Error connecting to server.</p>'; }
}

async function showStatuteModal(encodedName, displayName, totalRefs) {
    const modal = document.getElementById('case-modal');
    const body = document.getElementById('modal-body');
    body.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:4rem;"><i data-lucide="loader" class="animate-spin" style="width:32px;height:32px;margin:0 auto 1rem;"></i>Retrieving referencing cases...</p>';
    modal.classList.remove('hidden');
    lucide.createIcons();
    
    try {
        const res = await fetch(`${API}/statute/${encodedName}/cases`);
        const cases = await res.json();
        
        // Concordance check inside modal
        let alertHtml = '';
        const actMatch = displayName.toUpperCase().match(/SECTION\s+(\d+[A-Z]*)\s+OF\s+(?:THE\s+)?(INDIAN PENAL CODE|CODE OF CRIMINAL PROCEDURE|EVIDENCE ACT)/);
        if (actMatch) {
            const sec = actMatch[1];
            const actType = actMatch[2].includes("PENAL") ? "IPC" : (actMatch[2].includes("PROCEDURE") ? "CrPC" : "IEA");
            const map = CONCORDANCE_DATA[actType][sec];
            if (map) {
                alertHtml = `
                    <div class="modal-statute-reform-alert" style="margin-top: 1rem;">
                        <div class="alert-header"><i data-lucide="alert-circle"></i> Criminal Reform Equivalency</div>
                        <div class="alert-body">
                            Under the modern criminal codes, this section corresponds to: 
                            <strong>Section ${map.newSection} of the ${actType === 'IPC' ? 'BNS' : (actType === 'CrPC' ? 'BNSS' : 'BSA')}</strong> (${map.title}).
                        </div>
                    </div>
                `;
            }
        }

        body.innerHTML = `
            <div class="modal-case-name">📜 ${displayName}</div>
            <div class="modal-meta">
                <span class="modal-meta-item"><i data-lucide="bookmark"></i> ${totalRefs} total references</span>
                <span class="modal-meta-item"><i data-lucide="file-text"></i> ${cases.length} cases in graph</span>
            </div>
            
            ${alertHtml}
            
            <div class="modal-section">
                <h3>📁 Case Citations (${cases.length})</h3>
                ${cases.length ? `
                <ul class="modal-list">${cases.map(c => `
                    <li onclick="openCaseFromModal('${c.case_id}')">${c.case_name} <span style='color:var(--text-muted);font-size:0.75rem;'>${c.court || ''} · ${c.year || ''}</span></li>
                `).join('')}</ul>` : '<p style="color:var(--text-muted)">No referencing cases indexed.</p>'}
            </div>
        `;
        lucide.createIcons();
    } catch(e) {
        body.innerHTML = '<p style="color:var(--accent-rose);">Error loading statute records.</p>';
    }
}

// ─── Concordance Tool Logic ──────────────────────────────
function initConcordanceTool() {
    const typeSelect = document.getElementById('concordance-law-type');
    const input = document.getElementById('concordance-section-input');
    const btn = document.getElementById('btn-concordance-lookup');
    const resultBox = document.getElementById('concordance-result');
    
    // Add enter key trigger
    input.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            btn.click();
        }
    });

    btn.addEventListener('click', () => {
        const law = typeSelect.value;
        const section = input.value.trim();
        
        if (!section) {
            resultBox.classList.add('hidden');
            return;
        }
        
        const res = lookupConcordance(law, section);
        resultBox.classList.remove('hidden');
        
        if (res) {
            if (res.direction === 'old_to_new') {
                resultBox.innerHTML = `
                    <div class="concordance-alert-header">
                        <i data-lucide="check-circle" style="width:16px;height:16px;color:var(--accent-emerald);"></i> Match Found (July 2024 Transition)
                    </div>
                    <div class="concordance-mapping-title">
                        <span class="concordance-law-badge">${res.oldAct}</span> Section ${res.oldSec} 
                        <span style="margin:0 0.5rem;color:var(--accent-amber);">➔</span> 
                        <span class="concordance-law-badge" style="background:rgba(52,211,153,0.15);color:var(--accent-emerald);">${res.newAct}</span> Section ${res.newSec}
                    </div>
                    <div style="font-weight:700;margin-top:0.4rem;color:var(--text-bright);font-size:0.9rem;">
                        Subject Matter: ${res.title}
                    </div>
                    <div class="concordance-mapping-desc" style="margin-top:0.3rem;">
                        ${res.desc}
                    </div>
                `;
            } else {
                resultBox.innerHTML = `
                    <div class="concordance-alert-header">
                        <i data-lucide="check-circle" style="width:16px;height:16px;color:var(--accent-emerald);"></i> Match Found (July 2024 Transition)
                    </div>
                    <div class="concordance-mapping-title">
                        <span class="concordance-law-badge" style="background:rgba(52,211,153,0.15);color:var(--accent-emerald);">${res.newAct}</span> Section ${res.newSec}
                        <span style="margin:0 0.5rem;color:var(--accent-amber);">➔</span> 
                        <span class="concordance-law-badge">${res.oldAct}</span> Section ${res.oldSec}
                    </div>
                    <div style="font-weight:700;margin-top:0.4rem;color:var(--text-bright);font-size:0.9rem;">
                        Subject Matter: ${res.title}
                    </div>
                    <div class="concordance-mapping-desc" style="margin-top:0.3rem;">
                        ${res.desc}
                    </div>
                `;
            }
        } else {
            resultBox.innerHTML = `
                <div class="concordance-alert-header" style="color:var(--accent-rose);">
                    <i data-lucide="x-circle" style="width:16px;height:16px;"></i> Provision Not Mapped
                </div>
                <div class="concordance-mapping-desc">
                    Section <strong>${section}</strong> under <strong>${law}</strong> was not found in the transition dictionary database. Make sure you entered a valid core section number (e.g., 302, 438, 125, 32).
                </div>
            `;
        }
        lucide.createIcons();
    });
}

function lookupConcordance(law, section) {
    const data = CONCORDANCE_DATA[law];
    if (!data) return null;
    
    const cleanSection = section.replace(/\s+/g, '').toUpperCase();
    
    // Direct search (Old to New)
    if (data[cleanSection]) {
        return {
            direction: 'old_to_new',
            oldSec: cleanSection,
            newSec: data[cleanSection].newSection,
            title: data[cleanSection].title,
            desc: data[cleanSection].desc,
            oldAct: law,
            newAct: law === 'IPC' ? 'BNS' : (law === 'CrPC' ? 'BNSS' : 'BSA')
        };
    }
    
    // Reverse search (New to Old)
    for (const [oldSec, info] of Object.entries(data)) {
        if (info.newSection === cleanSection) {
            return {
                direction: 'new_to_old',
                oldSec: oldSec,
                newSec: info.newSection,
                title: info.title,
                desc: info.desc,
                oldAct: law,
                newAct: law === 'IPC' ? 'BNS' : (law === 'CrPC' ? 'BNSS' : 'BSA')
            };
        }
    }
    
    return null;
}

// ─── Graph Explorer (Canvas-based Force Graph) ──────────
let nodes = [], edges = [], canvasWidth, canvasHeight, ctx;
let dragging = null, hovered = null, selectedNode = null;
let offsetX = 0, offsetY = 0;
let panX = 0, panY = 0, zoom = 1, isPanning = false, panStart = {};
let physicsEnabled = true;

const NODE_COLORS = { Case: '#6366f1', Judge: '#22d3ee', Statute: '#34d399' };
const NODE_SIZES = { Case: 6, Judge: 9, Statute: 7.5 };
const EDGE_COLORS = { CITES: '#6366f1', DECIDED: '#22d3ee', REFERS_TO: '#34d399' };

async function loadGraph() {
    const canvas = document.getElementById('graph-canvas');
    const container = document.getElementById('graph-container');
    ctx = canvas.getContext('2d');
    
    canvasWidth = container.clientWidth;
    canvasHeight = container.clientHeight;
    
    // Adjust scale for Retina displays
    canvas.width = canvasWidth * window.devicePixelRatio;
    canvas.height = canvasHeight * window.devicePixelRatio;
    canvas.style.width = canvasWidth + 'px';
    canvas.style.height = canvasHeight + 'px';
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // Setup graph legends
    let legend = container.querySelector('.graph-legend');
    if (!legend) {
        legend = document.createElement('div');
        legend.className = 'graph-legend';
        legend.innerHTML = `
            <div class="legend-item"><div class="legend-dot" style="background:#6366f1"></div>Case</div>
            <div class="legend-item"><div class="legend-dot" style="background:#22d3ee"></div>Judge</div>
            <div class="legend-item"><div class="legend-dot" style="background:#34d399"></div>Statute</div>
        `;
        container.appendChild(legend);
    }

    const filter = document.getElementById('graph-filter').value;
    const limit = document.getElementById('graph-limit').value;

    try {
        const res = await fetch(`${API}/graph/sample?limit=${limit}&type=${filter}`);
        graphData = await res.json();
        
        // Auto-configure neighborhood depth selectors
        document.getElementById('graph-depth').value = "all";
        
        initForceSimulation(graphData);
    } catch(e) {
        console.error('Graph load error:', e);
    }

    // Controls setup
    document.getElementById('btn-reload-graph').onclick = () => { nodes=[]; edges=[]; loadGraph(); };
    document.getElementById('btn-fit-graph').onclick = fitView;
    
    // Limits
    document.getElementById('graph-limit').oninput = (e) => {
        document.getElementById('graph-limit-label').textContent = e.target.value + ' nodes';
    };
    
    // Physics toggle
    const physToggle = document.getElementById('btn-physics-toggle');
    physToggle.onclick = () => {
        physicsEnabled = !physicsEnabled;
        physToggle.innerHTML = physicsEnabled ? '<i data-lucide="pause"></i> Pause' : '<i data-lucide="play"></i> Play';
        physToggle.className = physicsEnabled ? 'btn-secondary' : 'btn-primary';
        lucide.createIcons();
        if (physicsEnabled) {
            simulate();
        }
    };
    
    // Zoom Buttons
    document.getElementById('btn-zoom-in').onclick = () => {
        zoom = Math.min(5, zoom * 1.25);
        draw();
    };
    document.getElementById('btn-zoom-out').onclick = () => {
        zoom = Math.max(0.1, zoom / 1.25);
        draw();
    };

    // Graph Autocomplete search
    initGraphSearch();

    // Mouse listeners
    canvas.onmousedown = handleMouseDown;
    canvas.onmousemove = handleMouseMove;
    canvas.onmouseup = handleMouseUp;
    canvas.onwheel = handleWheel;
    canvas.ondblclick = handleDblClick;
    
    // Window resize
    window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
    const container = document.getElementById('graph-container');
    if (!container || !document.getElementById('section-graph').classList.contains('active')) return;
    const canvas = document.getElementById('graph-canvas');
    
    canvasWidth = container.clientWidth;
    canvasHeight = container.clientHeight;
    
    canvas.width = canvasWidth * window.devicePixelRatio;
    canvas.height = canvasHeight * window.devicePixelRatio;
    canvas.style.width = canvasWidth + 'px';
    canvas.style.height = canvasHeight + 'px';
    
    ctx = canvas.getContext('2d');
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    draw();
}

function initForceSimulation(data) {
    const nodeMap = {};
    nodes = data.nodes.map((n, i) => {
        const angle = (i / data.nodes.length) * Math.PI * 2;
        const radius = 180 + Math.random() * 120;
        const node = {
            ...n,
            x: canvasWidth / 2 + Math.cos(angle) * radius,
            y: canvasHeight / 2 + Math.sin(angle) * radius,
            vx: 0, vy: 0,
            size: NODE_SIZES[n.type] || 6,
            color: NODE_COLORS[n.type] || '#6366f1',
        };
        nodeMap[n.id] = node;
        return node;
    });

    edges = data.edges.filter(e => nodeMap[e.source] && nodeMap[e.target]).map(e => ({
        ...e,
        sourceNode: nodeMap[e.source],
        targetNode: nodeMap[e.target],
        color: EDGE_COLORS[e.type] || '#333',
    }));

    panX = 0; panY = 0; zoom = 1;
    selectedNode = null;
    hovered = null;
    
    fitView();
    simulate();
}

function simulate() {
    if (!physicsEnabled) return;
    let iterations = 0;
    const maxIter = 150;

    function tick() {
        if (!physicsEnabled) return;
        iterations++;
        
        // Repulsion forces (nodes separation)
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                let dx = nodes[j].x - nodes[i].x;
                let dy = nodes[j].y - nodes[i].y;
                let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                
                // Repel more strongly if they are closer
                let repelStrength = 1200;
                if (dist < 100) repelStrength = 2200;
                
                let force = repelStrength / (dist * dist);
                let fx = (dx / dist) * force;
                let fy = (dy / dist) * force;
                nodes[i].vx -= fx; nodes[i].vy -= fy;
                nodes[j].vx += fx; nodes[j].vy += fy;
            }
        }

        // Attraction forces (connected edges)
        for (const e of edges) {
            let dx = e.targetNode.x - e.sourceNode.x;
            let dy = e.targetNode.y - e.sourceNode.y;
            let dist = Math.sqrt(dx * dx + dy * dy) || 1;
            
            // Core distance length
            const targetLength = 100;
            let force = (dist - targetLength) * 0.015;
            let fx = (dx / dist) * force;
            let fy = (dy / dist) * force;
            e.sourceNode.vx += fx; e.sourceNode.vy += fy;
            e.targetNode.vx -= fx; e.targetNode.vy -= fy;
        }

        // Gravity center force
        for (const n of nodes) {
            n.vx += (canvasWidth / 2 - n.x) * 0.0012;
            n.vy += (canvasHeight / 2 - n.y) * 0.0012;
        }

        // Velocities damping application
        const damping = 0.82;
        for (const n of nodes) {
            if (n === dragging) continue;
            n.vx *= damping;
            n.vy *= damping;
            n.x += n.vx;
            n.y += n.vy;
        }

        draw();
        if (iterations < maxIter) {
            requestAnimationFrame(tick);
        }
    }
    tick();
}

function draw() {
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    
    // Grid alignment lines in background
    drawGridPattern();
    
    ctx.save();
    ctx.translate(panX, panY);
    ctx.scale(zoom, zoom);

    const activeNode = hovered || selectedNode;
    
    // Find active neighbors list
    const activeNeighbors = new Set();
    if (activeNode) {
        activeNeighbors.add(activeNode.id);
        edges.forEach(e => {
            if (e.source === activeNode.id) activeNeighbors.add(e.target);
            if (e.target === activeNode.id) activeNeighbors.add(e.source);
        });
    }

    // ─── Draw Edges ───
    for (const e of edges) {
        const isRelated = activeNode && (e.source === activeNode.id || e.target === activeNode.id);
        
        ctx.strokeStyle = e.color;
        
        if (activeNode) {
            if (isRelated) {
                ctx.lineWidth = 1.8;
                ctx.globalAlpha = 0.95;
            } else {
                ctx.lineWidth = 0.4;
                ctx.globalAlpha = 0.04; // Extremely dimmed
            }
        } else {
            ctx.lineWidth = 0.6;
            ctx.globalAlpha = 0.35;
        }
        
        ctx.beginPath();
        ctx.moveTo(e.sourceNode.x, e.sourceNode.y);
        ctx.lineTo(e.targetNode.x, e.targetNode.y);
        ctx.stroke();
        
        // Draw small flow connection arrows on highlighted paths
        if (isRelated) {
            drawArrowhead(ctx, e.sourceNode.x, e.sourceNode.y, e.targetNode.x, e.targetNode.y, e.targetNode.size + 1);
        }
    }
    
    ctx.globalAlpha = 1.0;

    // ─── Draw Nodes ───
    for (const n of nodes) {
        const isHoveredNode = n === hovered;
        const isSelectedNode = n === selectedNode;
        const isHighlight = !activeNode || activeNeighbors.has(n.id);
        
        if (activeNode && !isHighlight) {
            ctx.globalAlpha = 0.15; // Dimmed node
        } else {
            ctx.globalAlpha = 1.0;
        }

        const size = (isHoveredNode || isSelectedNode) ? n.size * 1.5 : n.size;
        
        // Node outer drop glow
        if (isHoveredNode || isSelectedNode) {
            ctx.shadowColor = n.color;
            ctx.shadowBlur = 15;
        }

        // Draw solid circle node
        ctx.fillStyle = n.color;
        ctx.beginPath();
        ctx.arc(n.x, n.y, size, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw inner white center core
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(n.x, n.y, size * 0.3, 0, Math.PI * 2);
        ctx.fill();

        ctx.shadowBlur = 0; // Reset glow

        // Labels display for highlighted/hovered sets
        const theme = document.documentElement.getAttribute('data-theme');
        const textCol = theme === 'light' ? '#1e293b' : '#f8fafc';
        const textShadow = theme === 'light' ? '#ffffff' : '#000000';
        
        if (isHoveredNode || isSelectedNode) {
            ctx.fillStyle = textCol;
            ctx.font = `bold ${12 / zoom}px var(--font-sans)`;
            ctx.textAlign = 'center';
            // Draw background text shadow rect or stroke
            ctx.strokeStyle = textShadow;
            ctx.lineWidth = 4;
            ctx.strokeText(n.label, n.x, n.y - size - 8);
            ctx.fillText(n.label, n.x, n.y - size - 8);
        } else if (activeNode && isHighlight && n.id !== activeNode.id) {
            // Draw permanent labels for neighbors on hover
            ctx.fillStyle = theme === 'light' ? '#475569' : '#94a3b8';
            ctx.font = `500 ${10 / zoom}px var(--font-sans)`;
            ctx.textAlign = 'center';
            ctx.strokeStyle = textShadow;
            ctx.lineWidth = 3;
            ctx.strokeText(n.label, n.x, n.y - size - 6);
            ctx.fillText(n.label, n.x, n.y - size - 6);
        }
    }

    ctx.restore();
}

function drawGridPattern() {
    const theme = document.documentElement.getAttribute('data-theme');
    const gridColor = theme === 'light' ? 'rgba(99, 102, 241, 0.03)' : 'rgba(99, 102, 241, 0.015)';
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 0.5;
    
    const gridSize = 40;
    
    // Draw columns
    for (let x = panX % gridSize; x < canvasWidth; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvasHeight);
        ctx.stroke();
    }
    // Draw rows
    for (let y = panY % gridSize; y < canvasHeight; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvasWidth, y);
        ctx.stroke();
    }
}

function drawArrowhead(ctx, fromx, fromy, tox, toy, offset) {
    const angle = Math.atan2(toy - fromy, tox - fromx);
    // Position arrow near target boundary
    const arrowX = tox - offset * Math.cos(angle);
    const arrowY = toy - offset * Math.sin(angle);
    
    const arrowSize = 6;
    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath();
    ctx.moveTo(arrowX, arrowY);
    ctx.lineTo(arrowX - arrowSize * Math.cos(angle - Math.PI/6), arrowY - arrowSize * Math.sin(angle - Math.PI/6));
    ctx.lineTo(arrowX - arrowSize * Math.cos(angle + Math.PI/6), arrowY - arrowSize * Math.sin(angle + Math.PI/6));
    ctx.closePath();
    ctx.fill();
}

function getMousePos(e) {
    const rect = e.target.getBoundingClientRect();
    return {
        x: (e.clientX - rect.left - panX) / zoom,
        y: (e.clientY - rect.top - panY) / zoom
    };
}

function findNode(mx, my) {
    for (let i = nodes.length - 1; i >= 0; i--) {
        const n = nodes[i];
        const dx = mx - n.x, dy = my - n.y;
        // Node hover margin threshold
        const limitSize = Math.max(n.size, 10);
        if (dx * dx + dy * dy < (limitSize + 8) * (limitSize + 8)) return n;
    }
    return null;
}

function handleMouseDown(e) {
    const pos = getMousePos(e);
    const node = findNode(pos.x, pos.y);
    if (node) {
        dragging = node;
        offsetX = pos.x - node.x;
        offsetY = pos.y - node.y;
    } else {
        isPanning = true;
        panStart = { x: e.clientX - panX, y: e.clientY - panY };
    }
}

function handleMouseMove(e) {
    const pos = getMousePos(e);
    const tooltip = document.getElementById('graph-tooltip');
    
    if (dragging) {
        dragging.x = pos.x - offsetX;
        dragging.y = pos.y - offsetY;
        draw();
    } else if (isPanning) {
        panX = e.clientX - panStart.x;
        panY = e.clientY - panStart.y;
        draw();
    } else {
        const node = findNode(pos.x, pos.y);
        if (node !== hovered) {
            hovered = node;
            e.target.style.cursor = node ? 'pointer' : 'grab';
            
            // Update tooltip overlay position and content
            if (node) {
                const rect = e.target.getBoundingClientRect();
                tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
                tooltip.style.top = (e.clientY - rect.top + 15) + 'px';
                
                let details = '';
                if (node.type === 'Case') details = `📅 Year: ${node.properties.year || 'N/A'}<br>🏢 Court: ${node.properties.court || 'N/A'}`;
                if (node.type === 'Judge') details = `⚖️ Decision Cases: ${node.properties.cases_decided || '—'}`;
                if (node.type === 'Statute') details = `📜 Provision: ${node.properties.section || '—'}<br>Act: ${node.properties.act_name || '—'}`;
                
                tooltip.innerHTML = `
                    <div class="tooltip-title">${node.label}</div>
                    <div class="tooltip-type" style="color:${NODE_COLORS[node.type]}">${node.type}</div>
                    <div style="font-size:0.75rem;margin-top:0.35rem;color:var(--text-secondary);line-height:1.4;">${details}</div>
                `;
                tooltip.classList.remove('hidden');
            } else {
                tooltip.classList.add('hidden');
            }
            draw();
        } else if (node) {
            // Keep tooltip tracking mouse coordinates
            const rect = e.target.getBoundingClientRect();
            tooltip.style.left = (e.clientX - rect.left + 15) + 'px';
            tooltip.style.top = (e.clientY - rect.top + 15) + 'px';
        }
    }
}

function handleMouseUp() {
    dragging = null;
    isPanning = false;
}

function handleWheel(e) {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.90 : 1.10;
    zoom = Math.max(0.1, Math.min(5, zoom * factor));
    draw();
}

function handleDblClick(e) {
    const pos = getMousePos(e);
    const node = findNode(pos.x, pos.y);
    if (node) {
        if (node.type === 'Case') {
            showCaseModal(node.id);
        } else {
            showNodeDetail(node);
        }
    }
}

// Autocomplete lookup in graph toolbar
function initGraphSearch() {
    const input = document.getElementById('graph-node-search');
    const dropdown = document.getElementById('graph-search-results');
    
    input.value = '';
    
    input.addEventListener('input', () => {
        const val = input.value.trim().toLowerCase();
        if (!val) {
            dropdown.classList.remove('active');
            return;
        }
        
        const matched = nodes.filter(n => n.label.toLowerCase().includes(val)).slice(0, 10);
        if (!matched.length) {
            dropdown.innerHTML = '<div class="graph-search-item" style="color:var(--text-muted);cursor:default;">No matches in graph</div>';
        } else {
            dropdown.innerHTML = matched.map(n => `
                <div class="graph-search-item" data-id="${n.id}">
                    <span style="font-weight:bold;color:${NODE_COLORS[n.type]};margin-right:0.4rem;">[${n.type[0]}]</span>${n.label}
                </div>
            `).join('');
        }
        dropdown.classList.add('active');
        
        dropdown.querySelectorAll('.graph-search-item').forEach(item => {
            if (item.dataset.id) {
                item.onclick = () => {
                    const targetNode = nodes.find(n => n.id === item.dataset.id);
                    dropdown.classList.remove('active');
                    input.value = targetNode.label;
                    if (targetNode) {
                        focusNodeOnCanvas(targetNode);
                    }
                };
            }
        });
    });
    
    // Close dropdown on clicking outside
    document.addEventListener('click', (e) => {
        if (e.target !== input) dropdown.classList.remove('active');
    });
    
    // Wire Neighborhood mode depth filter
    const depthSelect = document.getElementById('graph-depth');
    depthSelect.onchange = async () => {
        const mode = depthSelect.value;
        if (mode === 'all') {
            // Restore full graph
            loadGraph();
            return;
        }
        
        const focus = selectedNode || hovered;
        if (!focus) {
            alert("Please double-click or search a node first to define a focus center for the Neighborhood filter.");
            depthSelect.value = "all";
            return;
        }
        
        // Fetch neighborhood data
        try {
            const res = await fetch(`${API}/graph/neighborhood/${focus.id}?depth=${mode}`);
            const data = await res.json();
            
            // Re-render focusing only on neighborhood components
            initForceSimulation(data);
            
            // Re-find and lock focus node center in new set
            const newFocus = nodes.find(n => n.id === focus.id);
            if (newFocus) {
                selectedNode = newFocus;
                focusNodeOnCanvas(newFocus);
            }
        } catch(e) {
            console.error("Neighborhood fetch error:", e);
        }
    };
}

// Center and zoom animation on focus node
function focusNodeOnCanvas(node) {
    const targetZoom = 1.35;
    const targetPanX = canvasWidth / 2 - node.x * targetZoom;
    const targetPanY = canvasHeight / 2 - node.y * targetZoom;
    
    let startTime = null;
    const duration = 600; // ease animate duration
    
    const startZoom = zoom;
    const startPanX = panX;
    const startPanY = panY;
    
    selectedNode = node;
    
    function step(timestamp) {
        if (!startTime) startTime = timestamp;
        const progress = Math.min((timestamp - startTime) / duration, 1);
        
        // Ease Out Cubic function
        const ease = 1 - Math.pow(1 - progress, 3);
        
        zoom = startZoom + (targetZoom - startZoom) * ease;
        panX = startPanX + (targetPanX - startPanX) * ease;
        panY = startPanY + (targetPanY - startPanY) * ease;
        
        draw();
        
        if (progress < 1) {
            requestAnimationFrame(step);
        }
    }
    requestAnimationFrame(step);
    
    // Open detail panel
    showNodeDetail(node);
}

function showNodeDetail(node) {
    const panel = document.getElementById('node-detail-panel');
    const content = document.getElementById('node-detail-content');
    const p = node.properties || {};
    
    let html = `
        <div class="detail-title">${node.label}</div>
        <span class="detail-type" style="background:rgba(99,102,241,0.15);color:${NODE_COLORS[node.type]}">${node.type}</span>
    `;
    
    if (node.type === 'Judge') {
        html += '<div class="detail-section"><h4>Properties</h4>';
        html += `<div class="detail-prop"><span class="detail-prop-key">Author Full Name</span><span class="detail-prop-val">Justice ${p.name}</span></div>`;
        html += '</div>';
    } else if (node.type === 'Statute') {
        const hasBns = isOldCriminalLaw(p.full_reference || node.label);
        let concordanceText = '';
        if (hasBns && p.section) {
            const actType = p.full_reference.toUpperCase().includes("PENAL") ? "IPC" : (p.full_reference.toUpperCase().includes("PROCEDURE") ? "CrPC" : "IEA");
            const lookup = CONCORDANCE_DATA[actType][p.section];
            if (lookup) {
                concordanceText = `
                    <div style="margin-top:0.75rem;padding:0.75rem;border:1px solid rgba(251,191,36,0.3);background:rgba(251,191,36,0.06);border-radius:6px;font-size:0.75rem;line-height:1.45;">
                        <span style="color:var(--accent-amber);font-weight:700;">⚠️ Criminal Law Reform Alert</span><br>
                        Under the 2023 penal updates, this section maps to: <strong>Section ${lookup.newSection} of the ${actType === 'IPC' ? 'BNS' : (actType === 'CrPC' ? 'BNSS' : 'BSA')}</strong>.
                    </div>
                `;
            }
        }

        html += '<div class="detail-section"><h4>Properties</h4>';
        html += `<div class="detail-prop"><span class="detail-prop-key">Section Code</span><span class="detail-prop-val">${p.section || ''}</span></div>`;
        html += `<div class="detail-prop"><span class="detail-prop-key">Statutory Act</span><span class="detail-prop-val">${p.act_name || ''}</span></div>`;
        html += concordanceText;
        html += '</div>';
    }
    
    // Connected entities count
    const connectedEdges = edges.filter(e => e.source === node.id || e.target === node.id);
    html += `
        <div class="detail-section">
            <h4>Network Connectivity</h4>
            <div class="detail-prop"><span class="detail-prop-key">Linked Nodes</span><span class="detail-prop-val" style="font-family:var(--font-mono)">${connectedEdges.length} connections</span></div>
        </div>
    `;
    
    // Option button to view caseload/citations list
    if (node.type === 'Judge') {
        html += `<button class="btn-primary full-width" style="margin-top:1.5rem;" onclick="closeModal(); showJudgeModal('${encodeURIComponent(p.name)}', '${p.name.replace(/'/g, "\\'")}', ${connectedEdges.length})">View Judge Caseload</button>`;
    } else if (node.type === 'Statute') {
        html += `<button class="btn-primary full-width" style="margin-top:1.5rem;" onclick="closeModal(); showStatuteModal('${encodeURIComponent(p.full_reference || node.label)}', '${(p.full_reference || node.label).replace(/'/g, "\\'")}', ${connectedEdges.length})">View Statutes Cases</button>`;
    }
    
    content.innerHTML = html;
    panel.classList.remove('hidden');
    
    document.getElementById('close-detail').onclick = () => {
        panel.classList.add('hidden');
        selectedNode = null;
        draw();
    };
}

function fitView() {
    if (!nodes.length) return;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const n of nodes) {
        minX = Math.min(minX, n.x); maxX = Math.max(maxX, n.x);
        minY = Math.min(minY, n.y); maxY = Math.max(maxY, n.y);
    }
    const padding = 60;
    const w = maxX - minX + padding * 2;
    const h = maxY - minY + padding * 2;
    zoom = Math.min(canvasWidth / w, canvasHeight / h, 1.8);
    panX = canvasWidth / 2 - (minX + maxX) / 2 * zoom;
    panY = canvasHeight / 2 - (minY + maxY) / 2 * zoom;
    draw();
}
