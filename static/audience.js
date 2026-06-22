let ws;
let state = null;
let localTimerRemaining = 0;
let animationFrameId = null;
let buzzerPlayed = false;
let lastSecondPlayed = null;

// Connect to WebSocket
function connectWS() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  ws = new WebSocket(wsUrl);
  
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'state') {
      const oldState = state;
      state = msg.data;
      
      handleAudioCues(oldState, state);
      
      // Reset buzzer and beep tracking flags on reset or state changes back to running
      if (oldState && state && oldState.timer.state !== 'running' && state.timer.state === 'running') {
        buzzerPlayed = false;
        lastSecondPlayed = null;
      }
      if (state && state.timer.state !== 'running') {
        lastSecondPlayed = null;
      }
      if (state && state.timer.state === 'idle') {
        buzzerPlayed = false;
      }
      
      renderAudience();
    }
  };
  
  ws.onclose = () => {
    setTimeout(connectWS, 3000);
  };
}

// Sound effects removed
function playSoundFile(filename) {}
function playBuzzerSound() {}
function handleAudioCues(oldState, state) {}

// Format seconds into MM:SS
function formatTime(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Animation frame loop for timer countdown
function tickTimer() {
  if (!state || !state.timer) {
    animationFrameId = requestAnimationFrame(tickTimer);
    return;
  }
  
  const timer = state.timer;
  const display = document.getElementById("giant-timer-display");
  
  if (timer.state === 'countdown') {
    display.innerText = timer.countdownValue;
    display.className = "giant-timer";
  } else if (timer.state === 'running') {
    const elapsedSeconds = (Date.now() - timer.lastStartedAt) / 1000;
    localTimerRemaining = Math.max(0, timer.remaining - elapsedSeconds);
    
    display.innerText = formatTime(localTimerRemaining);
    
    // Countdown last 5 seconds beep trigger
    const displayedSeconds = Math.floor(localTimerRemaining);
    if (displayedSeconds <= 5 && displayedSeconds >= 1) {
      if (lastSecondPlayed !== displayedSeconds) {
        lastSecondPlayed = displayedSeconds;
        playSoundFile('beep.mp3');
      }
    }
    
    // End trigger
    if (localTimerRemaining <= 0 && !buzzerPlayed) {
      buzzerPlayed = true;
      playSoundFile('end.wav');
    }
    
    // Styling states
    if (localTimerRemaining <= 10 && localTimerRemaining > 0) {
      display.className = "giant-timer warning";
    } else if (localTimerRemaining <= 0) {
      display.className = "giant-timer finished";
    } else {
      display.className = "giant-timer";
    }
  } else {
    localTimerRemaining = timer.remaining;
    display.innerText = formatTime(localTimerRemaining);
    
    if (timer.state === 'paused') {
      if (localTimerRemaining <= 10 && localTimerRemaining > 0) {
        display.className = "giant-timer warning";
      } else {
        display.className = "giant-timer paused";
      }
    } else if (timer.state === 'finished') {
      display.className = "giant-timer finished";
      if (!buzzerPlayed) {
        buzzerPlayed = true;
        playSoundFile('end.wav');
      }
    } else {
      display.className = "giant-timer";
    }
  }
  
  animationFrameId = requestAnimationFrame(tickTimer);
}

// Update Teams and Header Text
function renderAudience() {
  if (!state) return;
  
  const activeId = state.settings.activeMatchId;
  const allMatches = [...state.matches, ...state.playoffBracket.matches];
  const activeMatch = allMatches.find(m => m.id === activeId);
  
  const header = document.getElementById("match-header-title");
  
  if (activeMatch) {
    header.innerText = activeMatch.name || (activeMatch.type === 'quali' ? `Q${getMatchNumber(activeMatch.id)}` : 'Playoff');
    
    // Red Side details
    const nameA = activeMatch.teamAId ? getTeamName(activeMatch.teamAId) : `(${describeSlot(activeMatch.slotA)})`;
    const botA = activeMatch.teamAId ? getTeamRobot(activeMatch.teamAId) : "TBD";
    const rankA = activeMatch.teamAId ? getTeamRank(activeMatch.teamAId) : "Rank --";
    
    document.getElementById("teamA-name").innerText = escapeHTML(botA);
    document.getElementById("teamA-bot").innerText = nameA ? `Team: ${escapeHTML(nameA)}` : "";
    document.getElementById("teamA-rank").innerText = rankA;
    
    // Blue Side details
    const nameB = activeMatch.teamBId ? getTeamName(activeMatch.teamBId) : `(${describeSlot(activeMatch.slotB)})`;
    const botB = activeMatch.teamBId ? getTeamRobot(activeMatch.teamBId) : "TBD";
    const rankB = activeMatch.teamBId ? getTeamRank(activeMatch.teamBId) : "Rank --";
    
    document.getElementById("teamB-name").innerText = escapeHTML(botB);
    document.getElementById("teamB-bot").innerText = nameB ? `Team: ${escapeHTML(nameB)}` : "";
    document.getElementById("teamB-rank").innerText = rankB;
  } else {
    header.innerText = "BattleBots Arena";
    document.getElementById("teamA-name").innerText = "--";
    document.getElementById("teamA-bot").innerText = "--";
    document.getElementById("teamA-rank").innerText = "Rank --";
    document.getElementById("teamB-name").innerText = "--";
    document.getElementById("teamB-bot").innerText = "--";
    document.getElementById("teamB-rank").innerText = "Rank --";
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

function getTeamRank(id) {
  if (!state.rankings) return "--";
  const r = state.rankings.find(x => x.id === id);
  return r ? `#${r.rank}` : "Rank --";
}

function getMatchNumber(id) {
  const idx = state.matches.findIndex(m => m.id === id);
  return idx !== -1 ? idx + 1 : 0;
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
requestAnimationFrame(tickTimer);
