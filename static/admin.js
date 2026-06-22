let ws;
let state = null;
let localTimerRemaining = 0;
let animationFrameId = null;

// Connect to WebSocket server
function connectWS() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  ws = new WebSocket(wsUrl);
  
  ws.onopen = () => {
    console.log("WebSocket connected");
    document.getElementById("timer-status-badge").innerText = "CONNECTED";
  };
  
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'state') {
      state = msg.data;
      updateUI();
    }
  };
  
  ws.onclose = () => {
    console.log("WebSocket disconnected. Reconnecting in 3s...");
    document.getElementById("timer-status-badge").innerText = "DISCONNECTED";
    setTimeout(connectWS, 3000);
  };
}

// Switch dashboard tabs
function switchTab(tabId) {
  // Update active tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById(`nav-${tabId}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Update visible tab content panels
  document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
  const activeContent = document.getElementById(`tab-${tabId}`);
  if (activeContent) activeContent.classList.add('active');
}

// Format seconds into MM:SS
function formatTime(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Local Timer Interpolation loop for smooth UI rendering
function tickTimer() {
  if (!state || !state.timer) {
    animationFrameId = requestAnimationFrame(tickTimer);
    return;
  }
  
  const timer = state.timer;
  const display = document.getElementById("timer-display");
  if (!display) {
    animationFrameId = requestAnimationFrame(tickTimer);
    return;
  }
  
  if (timer.state === 'countdown') {
    display.innerText = timer.countdownValue;
    display.className = "timer-numbers";
    document.getElementById("timer-status-badge").innerText = "PRE-MATCH COUNTDOWN";
  } else if (timer.state === 'running') {
    const elapsedSeconds = (Date.now() - timer.lastStartedAt) / 1000;
    localTimerRemaining = Math.max(0, timer.remaining - elapsedSeconds);
    
    display.innerText = formatTime(localTimerRemaining);
    
    // Add pulsing states and warnings
    if (localTimerRemaining <= 10 && localTimerRemaining > 0) {
      display.className = "timer-numbers warning";
      document.getElementById("timer-status-badge").innerText = "CRITICAL COOLDOWN";
    } else if (localTimerRemaining <= 0) {
      display.className = "timer-numbers warning";
      document.getElementById("timer-status-badge").innerText = "TIME'S UP";
    } else {
      display.className = "timer-numbers";
      document.getElementById("timer-status-badge").innerText = "LIVE MATCH";
    }
  } else {
    localTimerRemaining = timer.remaining;
    display.innerText = formatTime(localTimerRemaining);
    
    if (timer.state === 'paused') {
      if (localTimerRemaining <= 10 && localTimerRemaining > 0) {
        display.className = "timer-numbers warning";
      } else {
        display.className = "timer-numbers paused";
      }
      document.getElementById("timer-status-badge").innerText = "PAUSED";
    } else if (timer.state === 'finished') {
      display.className = "timer-numbers warning";
      document.getElementById("timer-status-badge").innerText = "TIME'S UP";
    } else {
      display.className = "timer-numbers";
      document.getElementById("timer-status-badge").innerText = "IDLE";
    }
  }
  
  animationFrameId = requestAnimationFrame(tickTimer);
}

// Update the full UI from State
function updateUI() {
  if (!state) return;
  
  // Teams Count
  document.getElementById("teams-count").innerText = state.teams.length;
  
  // Local network link
  if (state.ip) {
    document.getElementById("network-ip-link").innerText = `http://${state.ip}:8000`;
  }
  
  // Rankings Lock checkbox state
  document.getElementById("lock-rankings-toggle").checked = state.settings.lockRankings;
  
  // Render Teams List
  const teamsList = document.getElementById("teams-list");
  teamsList.innerHTML = "";
  state.teams.forEach(t => {
    const teamDiv = document.createElement("div");
    teamDiv.className = "team-item";
    teamDiv.innerHTML = `
      <div class="team-info">
        <div class="team-name">${escapeHTML(t.robotName)}</div>
        <div class="bot-name">Team: ${escapeHTML(t.name)}</div>
      </div>
      <button onclick="deleteTeam('${t.id}')" class="btn btn-danger btn-icon" ${state.settings.lockRankings ? 'disabled' : ''}>Delete</button>
    `;
    teamsList.appendChild(teamDiv);
  });
  
  // Render Rankings Table
  const rankingsBody = document.getElementById("rankings-table-body");
  rankingsBody.innerHTML = "";
  if (state.rankings && state.rankings.length > 0) {
    state.rankings.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="badge-rank">${r.rank}</span></td>
        <td>
          <div style="font-weight: 600;">${escapeHTML(r.robotName)}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">Team: ${escapeHTML(r.name)}</div>
        </td>
        <td style="text-align: center; font-family: monospace;">${r.wins}-${r.losses}</td>
        <td style="text-align: center; font-weight: 600; color: var(--accent-blue);">${r.winPct}%</td>
        <td style="text-align: center; color: var(--text-muted);">${r.aowp}%</td>
      `;
      rankingsBody.appendChild(tr);
    });
  } else {
    rankingsBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 12px 0;">No rankings calculated. Register teams and play qualification matches.</td></tr>`;
  }
  
  // Render selectors
  updateManualMatchCreatorDropdowns();
  updatePlayoffSourceDropdowns();
  
  // Render Scheduled Matches for Creator Tab
  updateCreationMatchList();
  
  // Render matches list on Match Control tab
  const matchesList = document.getElementById("matches-list");
  if (matchesList) {
    matchesList.innerHTML = "";
    const allMatches = state.matches || [];
    if (allMatches.length > 0) {
      allMatches.forEach(m => {
        const isPlayoff = m.type !== "quali";
        const teamAName = m.teamAId ? getTeamName(m.teamAId) : `(${describeSlot(m.slotA)})`;
        const teamBName = m.teamBId ? getTeamName(m.teamBId) : `(${describeSlot(m.slotB)})`;
        
        const isActive = m.id === state.settings.activeMatchId;
        const isCompleted = m.status === 'completed';
        
        let winnerLabel = "";
        if (m.status === 'completed') {
          if (m.winnerId === m.teamAId) {
            winnerLabel = `<span class="match-teams-display"><span class="winner">${escapeHTML(teamAName)}</span> vs <span>${escapeHTML(teamBName)}</span></span>`;
          } else if (m.winnerId === m.teamBId) {
            winnerLabel = `<span class="match-teams-display"><span>${escapeHTML(teamAName)}</span> vs <span class="winner">${escapeHTML(teamBName)}</span></span>`;
          } else {
            winnerLabel = `<span class="match-teams-display"><span>${escapeHTML(teamAName)}</span> vs <span>${escapeHTML(teamBName)}</span></span>`;
          }
        } else {
          winnerLabel = `<span class="match-teams-display"><span>${escapeHTML(teamAName)}</span> vs <span>${escapeHTML(teamBName)}</span></span>`;
        }
        
        const matchTypeLabel = m.name ? escapeHTML(m.name) : (m.type === 'quali' ? `Q${allMatches.indexOf(m) + 1}` : 'Playoff');
        
        const row = document.createElement("div");
        row.className = `match-row-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isPlayoff ? 'playoff' : ''}`;
        row.onclick = () => selectActiveMatch(m.id);
        row.innerHTML = `
          <div class="match-meta-info">
            <div class="match-meta-name">${matchTypeLabel}</div>
            <div class="match-meta-time">${m.scheduledTime} | Duration: ${formatTime(m.duration)}</div>
          </div>
          <div style="display:flex; align-items:center; gap:10px;">
            ${winnerLabel}
            <span style="font-size:0.75rem; text-transform:uppercase; opacity:0.8;">[${m.status}]</span>
          </div>
        `;
        matchesList.appendChild(row);
      });
    } else {
      matchesList.innerHTML = `<div style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 20px 0;">No matches scheduled.</div>`;
    }
  }
  
  // Render Active Match details
  updateActiveMatchCard();
}

function getTeamName(id) {
  const t = state.teams.find(x => x.id === id);
  return t ? t.name : "Unknown Team";
}

function getTeamRobot(id) {
  const t = state.teams.find(x => x.id === id);
  return t ? t.robotName : "";
}

function getTeamRank(id) {
  if (!state.rankings) return "--";
  const r = state.rankings.find(x => x.id === id);
  return r ? `#${r.rank}` : "Rank --";
}

function describeSlot(slot) {
  if (!slot) return "Empty";
  if (slot.type === 'rank') return `Rank ${slot.value}`;
  if (slot.type === 'match_winner') {
    const pm = state.playoffBracket.matches.find(x => x.id === slot.value);
    return `Winner of ${pm ? pm.name : 'Playoff'}`;
  }
  return "TBD";
}

// Render the detailed dashboard card for the active selected match
function updateActiveMatchCard() {
  const activeId = state.settings.activeMatchId;
  const allMatches = [...state.matches, ...state.playoffBracket.matches];
  const activeMatch = allMatches.find(m => m.id === activeId);
  
  const btnA = document.getElementById("btn-win-A");
  const btnB = document.getElementById("btn-win-B");
  const scoringActions = document.getElementById("match-scoring-actions");
  
  if (activeMatch) {
    // Red Team
    const nameA = activeMatch.teamAId ? getTeamName(activeMatch.teamAId) : `(${describeSlot(activeMatch.slotA)})`;
    const botA = activeMatch.teamAId ? getTeamRobot(activeMatch.teamAId) : "TBD";
    const rankA = activeMatch.teamAId ? getTeamRank(activeMatch.teamAId) : "Rank --";
    
    document.getElementById("active-teamA-name").innerText = botA;
    document.getElementById("active-teamA-bot").innerText = nameA ? `Team: ${nameA}` : "";
    document.getElementById("active-teamA-rank").innerText = rankA;
    
    // Blue Team
    const nameB = activeMatch.teamBId ? getTeamName(activeMatch.teamBId) : `(${describeSlot(activeMatch.slotB)})`;
    const botB = activeMatch.teamBId ? getTeamRobot(activeMatch.teamBId) : "TBD";
    const rankB = activeMatch.teamBId ? getTeamRank(activeMatch.teamBId) : "Rank --";
    
    document.getElementById("active-teamB-name").innerText = botB;
    document.getElementById("active-teamB-bot").innerText = nameB ? `Team: ${nameB}` : "";
    document.getElementById("active-teamB-rank").innerText = rankB;
    
    // Check if match can be scored (must have both teams resolved)
    if (activeMatch.teamAId && activeMatch.teamBId) {
      btnA.style.display = "block";
      btnB.style.display = "block";
      scoringActions.style.display = activeMatch.status === "completed" ? "block" : "none";
      
      // Update Winner indicators on dashboard buttons
      if (activeMatch.winnerId === activeMatch.teamAId) {
        btnA.className = "btn btn-red-corner winner";
        btnA.innerText = "Winner (Red)";
        btnB.className = "btn btn-secondary";
        btnB.innerText = "Set Winner";
      } else if (activeMatch.winnerId === activeMatch.teamBId) {
        btnA.className = "btn btn-secondary";
        btnA.innerText = "Set Winner";
        btnB.className = "btn btn-blue-corner winner";
        btnB.innerText = "Winner (Blue)";
      } else {
        btnA.className = "btn btn-red-corner";
        btnA.innerText = "Win Red";
        btnB.className = "btn btn-blue-corner";
        btnB.innerText = "Win Blue";
      }
    } else {
      btnA.style.display = "none";
      btnB.style.display = "none";
      scoringActions.style.display = "none";
    }
  } else {
    // Reset to empty states
    document.getElementById("active-teamA-name").innerText = "--";
    document.getElementById("active-teamA-bot").innerText = "--";
    document.getElementById("active-teamA-rank").innerText = "Rank --";
    document.getElementById("active-teamB-name").innerText = "--";
    document.getElementById("active-teamB-bot").innerText = "--";
    document.getElementById("active-teamB-rank").innerText = "Rank --";
    
    btnA.style.display = "none";
    btnB.style.display = "none";
    scoringActions.style.display = "none";
  }
}

// Populates dropdown selections in Bracket Designer
function updatePlayoffSourceDropdowns() {
  const typeA = document.getElementById("playoff-slotA-type").value;
  const valASelect = document.getElementById("playoff-slotA-value");
  const currentValA = valASelect.value;
  
  const typeB = document.getElementById("playoff-slotB-type").value;
  const valBSelect = document.getElementById("playoff-slotB-value");
  const currentValB = valBSelect.value;
  
  // Populate Slot A
  valASelect.innerHTML = "";
  if (typeA === "rank") {
    const maxRank = state.teams.length || 8;
    for (let i = 1; i <= maxRank; i++) {
      valASelect.appendChild(new Option(`Rank ${i}`, i));
    }
  } else {
    const playoffMatches = state.playoffBracket.matches;
    playoffMatches.forEach(pm => {
      valASelect.appendChild(new Option(pm.name, pm.id));
    });
  }
  if (currentValA) valASelect.value = currentValA;
  
  // Populate Slot B
  valBSelect.innerHTML = "";
  if (typeB === "rank") {
    const maxRank = state.teams.length || 8;
    for (let i = 1; i <= maxRank; i++) {
      valBSelect.appendChild(new Option(`Rank ${i}`, i));
    }
  } else {
    const playoffMatches = state.playoffBracket.matches;
    playoffMatches.forEach(pm => {
      valBSelect.appendChild(new Option(pm.name, pm.id));
    });
  }
  if (currentValB) valBSelect.value = currentValB;
}

// --- REST CALL ACTIONS ---

async function defCall(url, method = "POST", body = null) {
  try {
    const headers = { 'Content-Type': 'application/json' };
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);
    
    const res = await fetch(url, options);
    if (!res.ok) {
      const err = await res.json();
      alert(`API Error: ${err.detail || 'Request failed'}`);
      return null;
    }
    return await res.json();
  } catch (e) {
    console.error(e);
    alert("Network request failed.");
    return null;
  }
}

async function addTeam() {
  const name = document.getElementById("team-name").value.trim();
  const robotName = document.getElementById("bot-name").value.trim();
  if (!name || !robotName) return;
  
  const res = await defCall("/api/teams", "POST", { name, robotName });
  if (res) {
    document.getElementById("team-name").value = "";
    document.getElementById("bot-name").value = "";
  }
}

async function deleteTeam(id) {
  if (confirm("Are you sure you want to delete this team? This will erase all their scheduled matches!")) {
    await defCall(`/api/teams/${id}`, "DELETE");
  }
}

async function generateQualiMatches() {
  const minMatches = parseInt(document.getElementById("quali-min-matches").value);
  const startTime = document.getElementById("quali-start-time").value;
  const endTime = document.getElementById("quali-end-time").value;
  const duration = parseInt(document.getElementById("match-duration-select").value);
  
  if (state.teams.length < 2) {
    alert("Please register at least 2 teams before generating a schedule.");
    return;
  }
  
  await defCall("/api/quali/generate", "POST", { minMatches, startTime, endTime, duration });
}

async function selectActiveMatch(id) {
  await defCall("/api/settings/active-match", "POST", { matchId: id });
}

async function loadPrevMatch() {
  const activeId = state.settings.activeMatchId;
  const allMatches = [...state.matches, ...state.playoffBracket.matches];
  const idx = allMatches.findIndex(m => m.id === activeId);
  if (idx > 0) {
    selectActiveMatch(allMatches[idx - 1].id);
  }
}

async function loadNextMatch() {
  const activeId = state.settings.activeMatchId;
  const allMatches = [...state.matches, ...state.playoffBracket.matches];
  const idx = allMatches.findIndex(m => m.id === activeId);
  if (idx >= 0 && idx < allMatches.length - 1) {
    selectActiveMatch(allMatches[idx + 1].id);
  }
}

async function controlTimer(action) {
  let body = { action };
  if (action === "reset") {
    const activeId = state.settings.activeMatchId;
    const allMatches = [...state.matches, ...state.playoffBracket.matches];
    const activeMatch = allMatches.find(m => m.id === activeId);
    body.duration = activeMatch ? activeMatch.duration : parseInt(document.getElementById("match-duration-select").value);
  }
  await defCall("/api/timer/control", "POST", body);
}

async function setWinner(corner) {
  const activeId = state.settings.activeMatchId;
  const allMatches = [...state.matches, ...state.playoffBracket.matches];
  const activeMatch = allMatches.find(m => m.id === activeId);
  if (!activeMatch) return;
  
  const winnerId = corner === 'A' ? activeMatch.teamAId : activeMatch.teamBId;
  await defCall(`/api/matches/${activeId}/winner`, "POST", { winnerId });
}

async function clearWinner() {
  const activeId = state.settings.activeMatchId;
  if (!activeId) return;
  await defCall(`/api/matches/${activeId}/winner`, "POST", { winnerId: null });
}

async function toggleRankingsLock(locked) {
  await defCall("/api/settings/lock-rankings", "POST", { lock: locked });
}

function toggleManualMatchType() {
  const type = document.getElementById("manual-match-type").value;
  const qualFields = document.getElementById("manual-qual-fields");
  const playoffFields = document.getElementById("manual-playoff-fields");
  
  if (type === "quali") {
    qualFields.style.display = "block";
    playoffFields.style.display = "none";
  } else {
    qualFields.style.display = "none";
    playoffFields.style.display = "block";
  }
}

function updateManualMatchCreatorDropdowns() {
  const teamASelect = document.getElementById("manual-team-A");
  const teamBSelect = document.getElementById("manual-team-B");
  if (!teamASelect || !teamBSelect) return;
  
  const currentValA = teamASelect.value;
  const currentValB = teamBSelect.value;
  
  teamASelect.innerHTML = "";
  teamBSelect.innerHTML = "";
  
  if (state.teams && state.teams.length > 0) {
    state.teams.forEach(t => {
      teamASelect.appendChild(new Option(t.name, t.id));
      teamBSelect.appendChild(new Option(t.name, t.id));
    });
  }
  
  if (currentValA) teamASelect.value = currentValA;
  if (currentValB) teamBSelect.value = currentValB;
}

async function submitManualMatchForm() {
  const type = document.getElementById("manual-match-type").value;
  const duration = parseInt(document.getElementById("manual-match-duration").value);
  
  if (type === "quali") {
    const teamAId = document.getElementById("manual-team-A").value;
    const teamBId = document.getElementById("manual-team-B").value;
    if (!teamAId || !teamBId) {
      alert("Please select both teams.");
      return;
    }
    if (teamAId === teamBId) {
      alert("A team cannot play against itself.");
      return;
    }
    
    await defCall("/api/quali/manual", "POST", { teamAId, teamBId, duration });
  } else {
    const slotAType = document.getElementById("playoff-slotA-type").value;
    const slotAValue = document.getElementById("playoff-slotA-value").value;
    const slotBType = document.getElementById("playoff-slotB-type").value;
    const slotBValue = document.getElementById("playoff-slotB-value").value;
    
    await defCall("/api/playoff/add", "POST", {
      slotAType, slotAValue, slotBType, slotBValue, duration
    });
  }
}

async function deleteMatch(matchId) {
  if (confirm("Are you sure you want to delete this match? This cannot be undone.")) {
    await defCall(`/api/matches/${matchId}`, "DELETE");
  }
}

async function reorderMatchTo(fromIndex, toIndex) {
  const allMatches = state.matches || [];
  if (fromIndex === toIndex || fromIndex < 0 || fromIndex >= allMatches.length || toIndex < 0 || toIndex >= allMatches.length) return;
  
  const matchesCopy = [...allMatches];
  const [movedItem] = matchesCopy.splice(fromIndex, 1);
  matchesCopy.splice(toIndex, 0, movedItem);
  
  const matchIds = matchesCopy.map(m => m.id);
  await defCall("/api/matches/reorder", "POST", { matchIds });
}

function updateCreationMatchList() {
  const matchesCreationList = document.getElementById("matches-creation-list");
  if (!matchesCreationList) return;
  
  matchesCreationList.innerHTML = "";
  
  const allMatches = state.matches || [];
  
  if (allMatches.length > 0) {
    allMatches.forEach((m, idx) => {
      const isPlayoff = m.type !== "quali";
      const teamAName = m.teamAId ? getTeamName(m.teamAId) : `(${describeSlot(m.slotA)})`;
      const teamBName = m.teamBId ? getTeamName(m.teamBId) : `(${describeSlot(m.slotB)})`;
      
      const isCompleted = m.status === 'completed';
      
      let winnerLabel = "";
      if (m.status === 'completed') {
        if (m.winnerId === m.teamAId) {
          winnerLabel = `<span class="match-teams-display"><span class="winner">${escapeHTML(teamAName)}</span> vs <span>${escapeHTML(teamBName)}</span></span>`;
        } else if (m.winnerId === m.teamBId) {
          winnerLabel = `<span class="match-teams-display"><span>${escapeHTML(teamAName)}</span> vs <span class="winner">${escapeHTML(teamBName)}</span></span>`;
        } else {
          winnerLabel = `<span class="match-teams-display"><span>${escapeHTML(teamAName)}</span> vs <span>${escapeHTML(teamBName)}</span></span>`;
        }
      } else {
        winnerLabel = `<span class="match-teams-display"><span>${escapeHTML(teamAName)}</span> vs <span>${escapeHTML(teamBName)}</span></span>`;
      }
      
      const matchTypeLabel = m.name ? escapeHTML(m.name) : (m.type === 'quali' ? `Q${allMatches.indexOf(m) + 1}` : 'Playoff');
      
      const isQual = m.type === "quali";
      const isRankingsLocked = state.settings.lockRankings;
      const canDelete = !(isQual && isRankingsLocked);
      
      const row = document.createElement("div");
      row.className = `match-row-item ${m.id === state.settings.activeMatchId ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isPlayoff ? 'playoff' : ''}`;
      row.draggable = true;
      row.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <svg class="drag-handle-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="9" cy="5" r="1"></circle>
            <circle cx="9" cy="12" r="1"></circle>
            <circle cx="9" cy="19" r="1"></circle>
            <circle cx="15" cy="5" r="1"></circle>
            <circle cx="15" cy="12" r="1"></circle>
            <circle cx="15" cy="19" r="1"></circle>
          </svg>
          <div class="match-meta-info">
            <div class="match-meta-name">${matchTypeLabel}</div>
            <div class="match-meta-time">${m.scheduledTime} | Duration: ${formatTime(m.duration)}</div>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
          ${winnerLabel}
          <span style="font-size:0.75rem; text-transform:uppercase; opacity:0.8;">[${m.status}]</span>
          <button onclick="deleteMatch('${m.id}')" class="btn btn-danger btn-icon" style="padding: 4px 8px; font-size: 0.75rem;" ${canDelete ? '' : 'disabled'}>Delete</button>
        </div>
      `;
      
      row.addEventListener('dragstart', (e) => {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', idx);
        row.classList.add('dragging');
        matchesCreationList.classList.add('dragging-active');
      });
      
      row.addEventListener('dragend', () => {
        row.classList.remove('dragging');
        matchesCreationList.classList.remove('dragging-active');
        document.querySelectorAll('#matches-creation-list .match-row-item').forEach(el => el.classList.remove('drag-over'));
      });
      
      row.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        row.classList.add('drag-over');
      });
      
      row.addEventListener('dragenter', (e) => {
        e.preventDefault();
        row.classList.add('drag-over');
      });
      
      row.addEventListener('dragleave', () => {
        row.classList.remove('drag-over');
      });
      
      row.addEventListener('drop', (e) => {
        e.preventDefault();
        row.classList.remove('drag-over');
        const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
        const toIdx = idx;
        if (!isNaN(fromIdx) && fromIdx !== toIdx) {
          reorderMatchTo(fromIdx, toIdx);
        }
      });
      
      matchesCreationList.appendChild(row);
    });
  } else {
    matchesCreationList.innerHTML = `<div style="text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 20px 0;">No matches scheduled.</div>`;
  }
}

async function resetTournament() {
  if (confirm("Are you sure you want to delete ALL teams, matches, brackets, and rankings? This cannot be undone.")) {
    await defCall("/api/reset", "POST");
  }
}

// Helpers
function escapeHTML(str) {
  if (!str) return "";
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

// On startup
connectWS();
tickTimer();
