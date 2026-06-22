let ws;
let state = null;

let currentLeftPanelMode = null; // 'leaderboard', 'playoff', 'playoff_empty'
let renderedGroupHtml = "";
let renderedLeaderboardHtml = "";

// Clock update
function updateClock() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  document.getElementById("local-clock").innerText = timeStr;
}
setInterval(updateClock, 1000);
updateClock();

// Connect to WebSocket
function connectWS() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  ws = new WebSocket(wsUrl);
  
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'state') {
      state = msg.data;
      renderPit();
    }
  };
  
  ws.onclose = () => {
    setTimeout(connectWS, 3000);
  };
}

// Rendering function
function renderPit() {
  if (!state) return;
  
  // Render Leaderboard or Playoff Schedule depending on rankings lock
  const leftHeader = document.getElementById("pit-left-header");
  
  if (state.settings.lockRankings) {
    if (leftHeader) leftHeader.innerText = "Playoff Schedule";
    
    // Filter out completed matches so we only show remaining playoffs
    const playoffMatches = state.matches.filter(m => m.type !== 'quali' && m.status !== 'completed');
    
    if (playoffMatches.length > 0) {
      let groupHtml = `<div class="playoff-group" style="display: flex; flex-direction: column; gap: 16px; margin-bottom: 16px;">`;
      playoffMatches.forEach(m => {
        const teamAName = m.teamAId ? getTeamRobot(m.teamAId) : `(${describeSlot(m.slotA)})`;
        const teamBName = m.teamBId ? getTeamRobot(m.teamBId) : `(${describeSlot(m.slotB)})`;
        const teamADetails = m.teamAId ? `Team ${getTeamName(m.teamAId)}` : "";
        const teamBDetails = m.teamBId ? `Team ${getTeamName(m.teamBId)}` : "";
        
        let statusBadge = "";
        let rowClass = "playoff-match-row";
        if (m.status === 'completed') {
          statusBadge = `<span class="badge-winner">Winner: ${m.winnerId === m.teamAId ? teamAName : teamBName}</span>`;
          rowClass += " completed";
        } else if (m.id === state.settings.activeMatchId) {
          statusBadge = `<span class="queue-badge" style="background: rgba(220, 38, 38, 0.2); border-color: var(--accent-red); color: var(--accent-red); padding: 4px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase;">LIVE</span>`;
          rowClass += " active";
        } else {
          statusBadge = `<span class="queue-badge" style="padding: 4px 8px; background: rgba(0, 242, 254, 0.1); border: 1px solid var(--glass-border-glow); border-radius: 6px; font-size: 0.8rem; font-weight: 700; color: var(--accent-cyan); text-transform: uppercase;">SCHEDULED</span>`;
        }
        
        const isWinnerA = m.status === 'completed' && m.winnerId === m.teamAId;
        const isWinnerB = m.status === 'completed' && m.winnerId === m.teamBId;
        
        groupHtml += `
          <div class="${rowClass}" style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--glass-border); border-radius: 12px; padding: 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="display: flex; flex-direction: column; gap: 4px; text-align: left;">
              <span style="font-size: 0.9rem; font-weight: 700; color: var(--accent-cyan); text-transform: uppercase; letter-spacing: 1px;">${escapeHTML(m.name || 'Playoff Match')}</span>
              <div style="display: flex; align-items: center; gap: 16px; margin-top: 8px;">
                <div style="text-align: left;">
                  <span style="font-size: 1.25rem; font-weight: 700; ${isWinnerA ? 'color: var(--accent-green);' : 'color: var(--text-main);'}">${escapeHTML(teamAName)}</span>
                  <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHTML(teamADetails)}</div>
                </div>
                <span style="font-weight: 800; color: var(--text-muted);">VS</span>
                <div style="text-align: left;">
                  <span style="font-size: 1.25rem; font-weight: 700; ${isWinnerB ? 'color: var(--accent-green);' : 'color: var(--text-main);'}">${escapeHTML(teamBName)}</span>
                  <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHTML(teamBDetails)}</div>
                </div>
              </div>
            </div>
            <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
              <span style="font-size: 0.85rem; color: var(--text-muted); font-family: monospace;">Time: ${m.scheduledTime || '--:--'}</span>
              ${statusBadge}
            </div>
          </div>
        `;
      });
      groupHtml += `</div>`;
      
      if (currentLeftPanelMode !== 'playoff' || groupHtml !== renderedGroupHtml) {
        currentLeftPanelMode = 'playoff';
        renderedGroupHtml = groupHtml;
        renderedLeaderboardHtml = "";
        
        scrollContent.innerHTML = groupHtml;
        const firstGroup = scrollContent.querySelector('.playoff-group');
        const H = firstGroup ? firstGroup.getBoundingClientRect().height + 16 : 0;
        const C = scrollContainer.clientHeight;
        
        if (H > 16) {
          const neededCopies = Math.max(2, Math.ceil(C / H) + 1);
          let finalHtml = "";
          for (let i = 0; i < neededCopies; i++) {
            finalHtml += groupHtml;
          }
          scrollContent.innerHTML = finalHtml;
        }
        resetScroller();
      }
    } else {
      const emptyHtml = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">No playoff matches scheduled. Check back later.</div>`;
      if (currentLeftPanelMode !== 'playoff_empty') {
        currentLeftPanelMode = 'playoff_empty';
        renderedGroupHtml = "";
        renderedLeaderboardHtml = "";
        scrollContent.innerHTML = emptyHtml;
        resetScroller();
      }
    }
  } else {
    if (leftHeader) leftHeader.innerText = "Current Leaderboard";
    
    let leaderboardRowsHtml = "";
    if (state.rankings && state.rankings.length > 0) {
      state.rankings.forEach(r => {
        leaderboardRowsHtml += `
          <tr>
            <td style="padding: 16px;"><span class="badge-rank">${r.rank}</span></td>
            <td style="padding: 16px; font-weight: 700; font-size: 1.1rem;">${escapeHTML(r.robotName)}</td>
            <td style="padding: 16px; color: var(--text-muted);">Team: ${escapeHTML(r.name)}</td>
            <td style="padding: 16px; text-align: center; font-family: monospace; font-size: 1rem;">${r.wins}-${r.losses}</td>
            <td style="padding: 16px; text-align: center; font-weight: 800; color: var(--accent-cyan); font-size: 1rem;">${r.winPct}%</td>
            <td style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 0.95rem;">${r.aowp}%</td>
          </tr>
        `;
      });
    } else {
      leaderboardRowsHtml = `<tr><td colspan="6" style="text-align: center; padding: 40px; color: var(--text-muted);">No teams registered or rankings available.</td></tr>`;
    }
    
    if (currentLeftPanelMode !== 'leaderboard' || leaderboardRowsHtml !== renderedLeaderboardHtml) {
      currentLeftPanelMode = 'leaderboard';
      renderedLeaderboardHtml = leaderboardRowsHtml;
      renderedGroupHtml = "";
      
      scrollContent.innerHTML = `
        <table style="width: 100%;">
          <thead>
            <tr style="position: sticky; top: 0; background: var(--bg-panel-solid); z-index: 10;">
              <th style="padding: 16px;">Rank</th>
              <th style="padding: 16px;">Robot</th>
              <th style="padding: 16px;">Team Name</th>
              <th style="padding: 16px; text-align: center;">Record</th>
              <th style="padding: 16px; text-align: center;">Win %</th>
              <th style="padding: 16px; text-align: center;">SOS %</th>
            </tr>
          </thead>
          <tbody id="standings-rows">
            ${leaderboardRowsHtml}
          </tbody>
        </table>
      `;
      resetScroller();
    }
  }

  // Find Last Completed Match
  const allMatches = [...state.matches, ...state.playoffBracket.matches];
  const completedMatches = allMatches.filter(m => m.status === 'completed');
  const lastMatch = completedMatches[completedMatches.length - 1];
  
  if (lastMatch) {
    const winnerId = lastMatch.winnerId;
    const loserId = winnerId === lastMatch.teamAId ? lastMatch.teamBId : lastMatch.teamAId;
    
    const winnerRobot = getTeamRobot(winnerId) || "Unknown";
    const loserRobot = getTeamRobot(loserId) || "Unknown";
    
    const label = lastMatch.name || (lastMatch.type === 'quali' ? `Q${completedMatches.length}` : 'Playoff');
    
    document.getElementById("last-match-label").innerText = label;
    document.getElementById("last-match-vs").innerText = `${winnerRobot} beat ${loserRobot}`;
  } else {
    document.getElementById("last-match-label").innerText = "Awaiting Matches";
    document.getElementById("last-match-vs").innerText = "No Matches Logged";
  }
  
  // Find Upcoming Matches (not completed, not active, scheduled or live)
  const activeId = state.settings.activeMatchId;
  const upcoming = allMatches.filter(m => m.status !== 'completed' && m.id !== activeId);
  
  const upcomingQueue = document.getElementById("upcoming-queue");
  upcomingQueue.innerHTML = "";
  
  if (upcoming.length > 0) {
    // Take next 2 upcoming matches
    const displayNext = upcoming.slice(0, 2);
    displayNext.forEach(m => {
      const robotA = m.teamAId ? getTeamRobot(m.teamAId) : `(${describeSlot(m.slotA)})`;
      const robotB = m.teamBId ? getTeamRobot(m.teamBId) : `(${describeSlot(m.slotB)})`;
      const badgeText = m.name || (m.type === 'quali' ? `Q${allMatches.indexOf(m) + 1}` : 'Playoff');
      
      const div = document.createElement("div");
      div.className = "queue-item";
      div.innerHTML = `
        <div>
          <span class="queue-badge">${escapeHTML(badgeText)}</span>
          <div class="queue-teams" style="margin-top: 5px;">${escapeHTML(robotA)} vs ${escapeHTML(robotB)}</div>
        </div>
        <div class="queue-time">${m.scheduledTime}</div>
      `;
      upcomingQueue.appendChild(div);
    });
  } else {
    upcomingQueue.innerHTML = `<div style="text-align: center; color: var(--text-muted); font-size: 1rem;">No more matches scheduled. Playoff bracket complete!</div>`;
  }
}

function getTeamName(id) {
  const t = state.teams.find(x => x.id === id);
  return t ? t.name : "TBD";
}

function getTeamRobot(id) {
  const t = state.teams.find(x => x.id === id);
  return t ? t.robotName : "";
}

function describeSlot(slot) {
  if (!slot) return "TBD";
  if (slot.type === 'rank') return `Rank ${slot.value}`;
  if (slot.type === 'match_winner') {
    const pm = state.playoffBracket.matches.find(x => x.id === slot.value);
    return `Winner of ${pm ? pm.name : 'Playoff'}`;
  }
  return "TBD";
}

// Scroller logic
let scrollY = 0;
let scrollState = 'waiting_top'; // 'waiting_top', 'scrolling', 'waiting_bottom'
let timerStart = Date.now();

const scrollContent = document.getElementById("scroll-content");
const scrollContainer = document.querySelector(".scroll-container");

function resetScroller() {
  scrollY = 0;
  scrollState = 'waiting_top';
  timerStart = Date.now();
  if (scrollContent) scrollContent.style.transform = `translateY(0px)`;
}

function animateScroller() {
  if (!scrollContent || !scrollContainer) {
    requestAnimationFrame(animateScroller);
    return;
  }
  
  const contentHeight = scrollContent.offsetHeight;
  const containerHeight = scrollContainer.clientHeight;
  
  if (state && state.settings && state.settings.lockRankings) {
    // Playoff Schedule: Continuous loop scroll
    const firstGroup = scrollContent.querySelector('.playoff-group');
    if (firstGroup) {
      const singleCopyHeight = firstGroup.getBoundingClientRect().height + 16;
      scrollY += 0.5; // Scroll speed (px/frame)
      if (scrollY >= singleCopyHeight) {
        scrollY = scrollY % singleCopyHeight;
      }
      scrollContent.style.transform = `translateY(${-scrollY}px)`;
    } else {
      scrollY = 0;
      scrollContent.style.transform = `translateY(0px)`;
    }
  } else {
    // Leaderboard: Classic scroll with pauses
    const maxScroll = contentHeight - containerHeight;
    
    if (maxScroll <= 0) {
      // No scroll needed, reset position
      scrollY = 0;
      scrollContent.style.transform = `translateY(0px)`;
      requestAnimationFrame(animateScroller);
      return;
    }
    
    const now = Date.now();
    
    if (scrollState === 'waiting_top') {
      if (now - timerStart > 4000) { // Hold at top for 4 seconds
        scrollState = 'scrolling';
      }
    } else if (scrollState === 'scrolling') {
      scrollY += 0.5; // Scroll speed (px/frame)
      if (scrollY >= maxScroll + 20) { // scroll past end slightly
        scrollY = maxScroll + 20;
        scrollState = 'waiting_bottom';
        timerStart = now;
      }
      scrollContent.style.transform = `translateY(${-scrollY}px)`;
    } else if (scrollState === 'waiting_bottom') {
      if (now - timerStart > 4000) { // Hold at bottom for 4 seconds
        scrollState = 'waiting_top';
        scrollY = 0;
        scrollContent.style.transform = `translateY(0px)`;
        timerStart = now;
      }
    }
  }
  
  requestAnimationFrame(animateScroller);
}

// Escaping
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

connectWS();
requestAnimationFrame(animateScroller);
