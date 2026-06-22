import os
import json
import socket
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="BattleBots Tournament Manager")

import sys
DB_FILE = os.environ.get("BATTLEBOTS_DB_FILE")
if not DB_FILE:
    if getattr(sys, 'frozen', False):
        DB_FILE = os.path.join(os.path.dirname(sys.executable), ".battle")
    else:
        DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".battle")


# State structure
state = {
    "settings": {
        "matchDuration": 180,  # Default 3 minutes in seconds
        "lockRankings": False,
        "activeMatchId": None
    },
    "teams": [],
    "matches": [],
    "playoffBracket": {
        "matches": []
      },
    "timer": {
        "state": "idle",       # 'idle', 'countdown', 'running', 'paused', 'finished'
        "duration": 180,
        "remaining": 180,
        "lastStartedAt": None, # Epoch ms timestamp
        "countdownValue": 0
    }
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()
active_timer_task: Optional[asyncio.Task] = None

# Match auto-naming engine based on type and order
def update_match_names():
    quali_count = 0
    playoff_count = 0
    for m in state["matches"]:
        if m.get("type") == "quali":
            quali_count += 1
            m["name"] = f"Q{quali_count}"
        else:
            playoff_count += 1
            m["name"] = f"F{playoff_count}"

# Returns a fresh, empty tournament state dictionary
def get_default_state():
    return {
        "settings": {
            "matchDuration": 180,
            "lockRankings": False,
            "activeMatchId": None
        },
        "teams": [],
        "matches": [],
        "playoffBracket": {
            "matches": []
        },
        "timer": {
            "state": "idle",
            "duration": 180,
            "remaining": 180,
            "lastStartedAt": None,
            "countdownValue": 0
        }
    }

# DB Persistence functions
def load_state():
    """Load state from DB_FILE into the in-memory state dict.
    If the file doesn't exist, resets in-memory state to defaults and saves.
    Migration (playoffBracket -> matches) is only run when data actually needs it.
    """
    global state
    # Clear and reset state to default first to avoid leakage from previously loaded database files
    state.clear()
    state.update(get_default_state())
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                loaded = json.load(f)
            # Merge loaded keys into in-memory state
            for key in list(state.keys()):
                if key in loaded:
                    state[key] = loaded[key]
            # Migration: if playoffBracket.matches has items, move them to the
            # unified matches list (one-time upgrade from old schema)
            migrated = False
            playoff_matches = state.get("playoffBracket", {}).get("matches", [])
            if playoff_matches:
                existing_ids = {m["id"] for m in state["matches"]}
                for pm in playoff_matches:
                    if pm["id"] not in existing_ids:
                        if "type" not in pm:
                            pm["type"] = "playoff"
                        state["matches"].append(pm)
                state["playoffBracket"]["matches"] = []
                migrated = True
            update_match_names()
            if migrated:
                # Only write back to disk when we actually changed something
                save_state()
        except Exception as e:
            print(f"Error loading state from {DB_FILE}: {e}")
            # File is corrupt - save the default state
            save_state()
    else:
        # No file yet - save the default state
        save_state()


def save_state():
    """Atomically write the current state to DB_FILE.
    Uses os.replace() which is atomic on Windows and POSIX — it replaces
    the destination even if it already exists, with no intermediate window
    where the file is missing.
    """
    try:
        temp_file = DB_FILE + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_file, DB_FILE)  # Atomic on both Windows and POSIX
    except Exception as e:
        print(f"Error saving state to {DB_FILE}: {e}")

# Helper to resolve IP address
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Load database at startup (disabled eagerly at module import; will load at server/event loop startup)
# load_state()

# Rankings Calculation Engine
def calculate_rankings_list():
    teams_map = {t["id"]: {"id": t["id"], "name": t["name"], "robotName": t["robotName"], "wins": 0, "losses": 0, "opponents": [], "played": 0} for t in state["teams"]}
    
    # Process qualification matches only
    for m in state["matches"]:
        if m.get("type") == "quali" and m.get("winnerId") and m.get("status") == "completed":
            tA = m["teamAId"]
            tB = m["teamBId"]
            winner = m["winnerId"]
            
            if tA in teams_map and tB in teams_map:
                teams_map[tA]["played"] += 1
                teams_map[tB]["played"] += 1
                teams_map[tA]["opponents"].append(tB)
                teams_map[tB]["opponents"].append(tA)
                
                if winner == tA:
                    teams_map[tA]["wins"] += 1
                    teams_map[tB]["losses"] += 1
                elif winner == tB:
                    teams_map[tB]["wins"] += 1
                    teams_map[tA]["losses"] += 1
                    
    # Calculate Win Pct
    for t_id, data in teams_map.items():
        data["winPct"] = (data["wins"] / data["played"]) if data["played"] > 0 else 0.0

    # Calculate Average Opponent Win Pct (AOWP)
    for t_id, data in teams_map.items():
        opponents = data["opponents"]
        if opponents:
            opp_win_pcts = [teams_map[opp_id]["winPct"] for opp_id in opponents if opp_id in teams_map]
            data["aowp"] = sum(opp_win_pcts) / len(opp_win_pcts) if opp_win_pcts else 0.0
        else:
            data["aowp"] = 0.0

    # Sort teams
    # 1. winPct (descending)
    # 2. aowp (descending)
    # 3. name (ascending)
    sorted_teams = sorted(
        teams_map.values(),
        key=lambda x: (-x["winPct"], -x["aowp"], x["name"].lower())
    )
    
    # Add rank index (1-based)
    rankings = []
    for index, t in enumerate(sorted_teams):
        rankings.append({
            "rank": index + 1,
            "id": t["id"],
            "name": t["name"],
            "robotName": t["robotName"],
            "wins": t["wins"],
            "losses": t["losses"],
            "played": t["played"],
            "winPct": round(t["winPct"] * 100, 1),
            "aowp": round(t["aowp"] * 100, 1)
        })
    return rankings

# Playoff Match Winner propagation
def propagate_playoff_winners():
    if not state["settings"]["lockRankings"]:
        return
    
    rankings = calculate_rankings_list()
    # Build maps
    rank_to_id = {r["rank"]: r["id"] for r in rankings}
    playoff_matches = [m for m in state["matches"] if m.get("type") != "quali"]
    match_map = {m["id"]: m for m in playoff_matches}
    
    # We do multiple passes to propagate fully through dependencies
    changed = True
    passes = 0
    while changed and passes < 10:
        changed = False
        for pm in playoff_matches:
            # Slot A
            old_teamA = pm["teamAId"]
            if pm["slotA"]["type"] == "rank":
                rank_val = int(pm["slotA"]["value"])
                pm["teamAId"] = rank_to_id.get(rank_val)
            elif pm["slotA"]["type"] == "match_winner":
                src_match_id = pm["slotA"]["value"]
                src_match = match_map.get(src_match_id)
                if src_match and src_match["status"] == "completed":
                    pm["teamAId"] = src_match["winnerId"]
                else:
                    pm["teamAId"] = None
                    
            if old_teamA != pm["teamAId"]:
                changed = True
                
            # Slot B
            old_teamB = pm["teamBId"]
            if pm["slotB"]["type"] == "rank":
                rank_val = int(pm["slotB"]["value"])
                pm["teamBId"] = rank_to_id.get(rank_val)
            elif pm["slotB"]["type"] == "match_winner":
                src_match_id = pm["slotB"]["value"]
                src_match = match_map.get(src_match_id)
                if src_match and src_match["status"] == "completed":
                    pm["teamBId"] = src_match["winnerId"]
                else:
                    pm["teamBId"] = None
                    
            if old_teamB != pm["teamBId"]:
                changed = True
        passes += 1

# Timer task runner
async def start_timer_task(duration_seconds: float, start_timestamp: int):
    global active_timer_task
    try:
        await asyncio.sleep(duration_seconds)
        # Check if the timer state is still running and matching the start session
        if (state["timer"]["state"] == "running" and 
            state["timer"]["lastStartedAt"] == start_timestamp):
            state["timer"]["state"] = "finished"
            state["timer"]["remaining"] = 0
            
            # Set match status to completed automatically?
            # BattleBots match ends, operator should verify winner first. We just mark the timer as finished.
            save_state()
            await manager.broadcast({"type": "state", "data": get_current_client_state()})
    except asyncio.CancelledError:
        pass

# Countdown task runner before match timer starts/resumes
async def run_countdown_and_start():
    global active_timer_task
    try:
        for count in [3, 2, 1]:
            state["timer"]["state"] = "countdown"
            state["timer"]["countdownValue"] = count
            await manager.broadcast({"type": "state", "data": get_current_client_state()})
            await asyncio.sleep(1.0)
            
        timer = state["timer"]
        timer["state"] = "running"
        timer["lastStartedAt"] = int(datetime.now().timestamp() * 1000)
        timer["countdownValue"] = 0
        
        active_timer_task = asyncio.create_task(
            start_timer_task(timer["remaining"], timer["lastStartedAt"])
        )
        
        active_id = state["settings"]["activeMatchId"]
        for m in state["matches"]:
            if m["id"] == active_id and m["status"] == "scheduled":
                m["status"] = "live"
                
        save_state()
        await manager.broadcast({"type": "state", "data": get_current_client_state()})
    except asyncio.CancelledError:
        pass

def get_current_client_state():
    # Enriches state with active rankings
    client_state = dict(state)
    client_state["rankings"] = calculate_rankings_list()
    client_state["ip"] = get_local_ip()
    client_state["playoffBracket"] = {
        "matches": [m for m in state["matches"] if m.get("type") != "quali"]
    }
    return client_state

# API Classes
class TeamCreate(BaseModel):
    name: str
    robotName: str

class WinnerUpdate(BaseModel):
    winnerId: Optional[str] = None

class ActiveMatchUpdate(BaseModel):
    matchId: Optional[str] = None

class TimerControlInput(BaseModel):
    action: str
    duration: Optional[int] = None

class ReorderMatchesInput(BaseModel):
    matchIds: List[str]

class QualiGenerateInput(BaseModel):
    minMatches: int
    startTime: str  # "HH:MM"
    endTime: str    # "HH:MM"
    duration: int   # seconds

class QualiManualInput(BaseModel):
    teamAId: str
    teamBId: str
    duration: int

class PlayoffMatchCreate(BaseModel):
    name: Optional[str] = None
    slotAType: str   # "rank" or "match_winner"
    slotAValue: str  # integer rank or playoff match ID
    slotBType: str
    slotBValue: str
    duration: int

# API Routing
@app.on_event("startup")
async def startup_event():
    """FastAPI startup hook. State was already loaded by launch_server() before
    Uvicorn started. We only need to handle the case where the timer was
    mid-run when the process was shut down.
    """
    global active_timer_task
    if state["timer"]["state"] == "running":
        last_started = state["timer"]["lastStartedAt"]
        if last_started:
            elapsed = (int(datetime.now().timestamp() * 1000) - last_started) / 1000.0
            remaining = max(0.0, state["timer"]["remaining"] - elapsed)
            if remaining > 0:
                state["timer"]["remaining"] = remaining
                active_timer_task = asyncio.create_task(
                    start_timer_task(remaining, last_started)
                )
            else:
                state["timer"]["state"] = "finished"
                state["timer"]["remaining"] = 0
                state["timer"]["lastStartedAt"] = None
                save_state()

@app.get("/api/state")
def get_state():
    return get_current_client_state()

@app.post("/api/reset")
async def reset_tournament():
    global state, active_timer_task
    if active_timer_task:
        active_timer_task.cancel()
        active_timer_task = None
        
    state = {
        "settings": {
            "matchDuration": 180,
            "lockRankings": False,
            "activeMatchId": None
        },
        "teams": [],
        "matches": [],
        "playoffBracket": {
            "matches": []
        },
        "timer": {
            "state": "idle",
            "duration": 180,
            "remaining": 180,
            "lastStartedAt": None,
            "countdownValue": 0
        }
    }
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return {"status": "success"}

@app.post("/api/teams")
async def add_team(team: TeamCreate):
    if state["settings"]["lockRankings"]:
        raise HTTPException(status_code=400, detail="Rankings are locked. Cannot add teams.")
    t_id = f"team_{int(datetime.now().timestamp() * 1000)}"
    new_team = {"id": t_id, "name": team.name, "robotName": team.robotName}
    state["teams"].append(new_team)
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return new_team

@app.delete("/api/teams/{team_id}")
async def delete_team(team_id: str):
    if state["settings"]["lockRankings"]:
        raise HTTPException(status_code=400, detail="Rankings are locked. Cannot delete teams.")
    state["teams"] = [t for t in state["teams"] if t["id"] != team_id]
    # Filter matches containing this team
    state["matches"] = [m for m in state["matches"] if m["teamAId"] != team_id and m["teamBId"] != team_id]
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return {"status": "success"}

@app.post("/api/quali/generate")
async def generate_quali(data: QualiGenerateInput):
    if state["settings"]["lockRankings"]:
        raise HTTPException(status_code=400, detail="Rankings are locked. Cannot generate matches.")
        
    teams = [t["id"] for t in state["teams"]]
    N = len(teams)
    if N < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 teams to generate matches.")
        
    # Circle Method round-robin scheduler
    elements = list(teams)
    if N % 2 != 0:
        elements.append(None)  # bye element
        
    M_elems = len(elements)
    rounds_per_cycle = M_elems - 1
    
    # Calculate cycles needed
    # In one cycle, each team plays at most N-1 matches
    matches_per_team_per_cycle = N - 1
    cycles_needed = int(abs(-data.minMatches // matches_per_team_per_cycle)) # ceil division
    
    generated_pairings = []
    
    for cycle in range(cycles_needed):
        # We start with the original elements list
        cycle_elements = list(elements)
        for r in range(rounds_per_cycle):
            # Pair elements
            for i in range(M_elems // 2):
                p1 = cycle_elements[i]
                p2 = cycle_elements[M_elems - 1 - i]
                if p1 is not None and p2 is not None:
                    generated_pairings.append((p1, p2))
            # Rotate elements: keep first element fixed, rotate remaining right
            cycle_elements = [cycle_elements[0]] + [cycle_elements[-1]] + cycle_elements[1:-1]

    J = len(generated_pairings)
    if J == 0:
        raise HTTPException(status_code=400, detail="No matches generated.")
        
    # Split the time block evenly
    try:
        start_t = datetime.strptime(data.startTime, "%H:%M")
        end_t = datetime.strptime(data.endTime, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM.")
        
    total_minutes = int((end_t - start_t).total_seconds() / 60)
    if total_minutes <= 0:
        raise HTTPException(status_code=400, detail="End time must be after start time.")
        
    # Generate schedule
    new_matches = []
    for idx, (tA, tB) in enumerate(generated_pairings):
        match_id = f"match_quali_{idx + 1}_{int(datetime.now().timestamp() * 1000)}"
        
        # Calculate time interval
        if J > 1:
            match_offset_mins = idx * (total_minutes / J)
        else:
            match_offset_mins = 0
            
        match_time = start_t + timedelta(minutes=match_offset_mins)
        time_str = match_time.strftime("%H:%M")
        
        new_matches.append({
            "id": match_id,
            "type": "quali",
            "round": (idx // (N // 2)) + 1,
            "teamAId": tA,
            "teamBId": tB,
            "winnerId": None,
            "status": "scheduled",
            "scheduledTime": time_str,
            "duration": data.duration
        })
        
    state["matches"] = new_matches
    state["settings"]["matchDuration"] = data.duration
    update_match_names()
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return new_matches

@app.post("/api/quali/manual")
async def add_manual_match(data: QualiManualInput):
    if state["settings"]["lockRankings"]:
        raise HTTPException(status_code=400, detail="Rankings are locked. Cannot add matches.")
    match_id = f"match_manual_{int(datetime.now().timestamp() * 1000)}"
    new_match = {
        "id": match_id,
        "type": "quali",
        "round": 0,  # 0 indicates manual
        "teamAId": data.teamAId,
        "teamBId": data.teamBId,
        "winnerId": None,
        "status": "scheduled",
        "scheduledTime": datetime.now().strftime("%H:%M"),
        "duration": data.duration
    }
    state["matches"].append(new_match)
    update_match_names()
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return new_match

@app.post("/api/playoff/add")
async def add_playoff_match(data: PlayoffMatchCreate):
    p_id = f"playoff_{int(datetime.now().timestamp() * 1000)}"
    
    try:
        valA = int(data.slotAValue) if data.slotAType == "rank" else data.slotAValue
    except ValueError:
        valA = data.slotAValue
        
    try:
        valB = int(data.slotBValue) if data.slotBType == "rank" else data.slotBValue
    except ValueError:
        valB = data.slotBValue

    new_pm = {
        "id": p_id,
        "type": "playoff",
        "name": data.name or "",
        "slotA": {"type": data.slotAType, "value": valA},
        "slotB": {"type": data.slotBType, "value": valB},
        "teamAId": None,
        "teamBId": None,
        "winnerId": None,
        "status": "scheduled",
        "duration": data.duration,
        "scheduledTime": "--:--"
    }
    
    state["matches"].append(new_pm)
    update_match_names()
    propagate_playoff_winners()
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return new_pm

@app.delete("/api/matches/{match_id}")
async def delete_match(match_id: str):
    match_to_delete = next((m for m in state["matches"] if m["id"] == match_id), None)
    if not match_to_delete:
        raise HTTPException(status_code=404, detail="Match not found.")
        
    if match_to_delete.get("type") == "quali" and state["settings"]["lockRankings"]:
        raise HTTPException(status_code=400, detail="Rankings are locked. Cannot delete qualification matches.")
        
    state["matches"] = [m for m in state["matches"] if m["id"] != match_id]
    if state["settings"]["activeMatchId"] == match_id:
        state["settings"]["activeMatchId"] = None
        
    update_match_names()
    propagate_playoff_winners()
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return {"status": "success"}

@app.post("/api/matches/reorder")
async def reorder_matches(data: ReorderMatchesInput):
    match_map = {m["id"]: m for m in state["matches"]}
    new_matches = []
    for m_id in data.matchIds:
        if m_id in match_map:
            new_matches.append(match_map[m_id])
    for m in state["matches"]:
        if m["id"] not in data.matchIds:
            new_matches.append(m)
            
    state["matches"] = new_matches
    update_match_names()
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return {"status": "success"}

@app.post("/api/settings/active-match")
async def set_active_match(data: ActiveMatchUpdate):
    matchId = data.matchId
    state["settings"]["activeMatchId"] = matchId
    
    match_duration = state["settings"]["matchDuration"]
    all_matches = state["matches"]
    active_m = next((m for m in all_matches if m["id"] == matchId), None)
    if active_m:
        match_duration = active_m["duration"]
        if active_m["status"] == "completed":
            state["timer"]["remaining"] = 0
            state["timer"]["state"] = "finished"
        else:
            state["timer"]["remaining"] = match_duration
            state["timer"]["state"] = "idle"
    else:
        state["timer"]["remaining"] = match_duration
        state["timer"]["state"] = "idle"
        
    state["timer"]["duration"] = match_duration
    state["timer"]["lastStartedAt"] = None
    
    global active_timer_task
    if active_timer_task:
        active_timer_task.cancel()
        active_timer_task = None
        
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return {"status": "success"}

@app.post("/api/settings/lock-rankings")
async def toggle_lock_rankings(lock: bool = Body(..., embed=True)):
    state["settings"]["lockRankings"] = lock
    if lock:
        propagate_playoff_winners()
    else:
        for pm in state["matches"]:
            if pm.get("type") != "quali":
                pm["teamAId"] = None
                pm["teamBId"] = None
                pm["winnerId"] = None
                pm["status"] = "scheduled"
            
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return {"status": "success"}

@app.post("/api/matches/{match_id}/winner")
async def set_winner(match_id: str, data: WinnerUpdate):
    winnerId = data.winnerId
    found = False
    for m in state["matches"]:
        if m["id"] == match_id:
            m["winnerId"] = winnerId
            m["status"] = "completed" if winnerId else "scheduled"
            found = True
            break
                
    if not found:
        raise HTTPException(status_code=404, detail="Match not found.")
        
    propagate_playoff_winners()
    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return {"status": "success"}

@app.post("/api/timer/control")
async def control_timer(data: TimerControlInput):
    global active_timer_task
    action = data.action
    duration = data.duration
    timer = state["timer"]
    
    if action == "start":
        if timer["state"] != "running" and timer["state"] != "countdown" and timer["remaining"] > 0:
            if active_timer_task:
                active_timer_task.cancel()
            active_timer_task = asyncio.create_task(
                run_countdown_and_start()
            )
            
    elif action == "pause":
        if timer["state"] == "running" or timer["state"] == "countdown":
            if timer["state"] == "running":
                elapsed = (int(datetime.now().timestamp() * 1000) - timer["lastStartedAt"]) / 1000.0
                timer["remaining"] = max(0.0, timer["remaining"] - elapsed)
            timer["state"] = "paused"
            timer["lastStartedAt"] = None
            timer["countdownValue"] = 0
            
            if active_timer_task:
                active_timer_task.cancel()
                active_timer_task = None
                
    elif action == "reset":
        if duration is not None:
            timer["duration"] = duration
        else:
            # Fallback: get the duration from the active match if available
            active_id = state["settings"]["activeMatchId"]
            all_matches = state["matches"]
            active_m = next((m for m in all_matches if m["id"] == active_id), None)
            if active_m:
                timer["duration"] = active_m["duration"]
            else:
                timer["duration"] = state["settings"]["matchDuration"]
                
        timer["remaining"] = timer["duration"]
        timer["state"] = "idle"
        timer["lastStartedAt"] = None
        timer["countdownValue"] = 0
        
        if active_timer_task:
            active_timer_task.cancel()
            active_timer_task = None
            
        active_id = state["settings"]["activeMatchId"]
        for m in state["matches"]:
            if m["id"] == active_id and m["status"] == "live":
                m["status"] = "scheduled"

    save_state()
    await manager.broadcast({"type": "state", "data": get_current_client_state()})
    return timer

# WebSocket Connection route
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "state", "data": get_current_client_state()})
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# HTML static routing
@app.get("/")
async def get_index():
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html not found"}

@app.get("/pit")
async def get_pit():
    pit_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "pit.html")
    if os.path.exists(pit_path):
        return FileResponse(pit_path)
    return {"error": "pit.html not found"}

@app.get("/audience")
async def get_audience():
    aud_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "audience.html")
    if os.path.exists(aud_path):
        return FileResponse(aud_path)
    return {"error": "audience.html not found"}

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    import sys
    import tkinter as tk
    from tkinter import filedialog, messagebox
    
    # Initialize a hidden tkinter root window
    root = tk.Tk()
    root.withdraw()
    
    # Prompt the user with options
    choice = messagebox.askyesnocancel(
        title="BattleBots Tournament Manager",
        message="Do you want to load an existing tournament?\n\n"
                "- Click 'Yes' to load an existing tournament file.\n"
                "- Click 'No' to create a new tournament file.\n"
                "- Click 'Cancel' to exit."
    )
    
    if choice is None:
        print("Startup cancelled by user.")
        root.destroy()
        sys.exit(0)
        
    if choice is True:
        # Load existing tournament
        path = filedialog.askopenfilename(
            title="Open Tournament File",
            filetypes=[("Battle Files", "*.battle"), ("JSON Files", "*.json"), ("All Files", "*.*")],
            defaultextension=".battle"
        )
        if not path:
            print("No file selected. Exiting.")
            root.destroy()
            sys.exit(0)
            
        path = os.path.abspath(path)
        if path.endswith(".battle.battle"):
            path = path[:-7]
        DB_FILE = path
        os.environ["BATTLEBOTS_DB_FILE"] = path
        load_state()
        print(f"Loaded tournament from: {DB_FILE}")
        
    else:
        # Create a new tournament
        path = filedialog.asksaveasfilename(
            title="Create New Tournament File",
            filetypes=[("Battle Files", "*.battle"), ("All Files", "*.*")],
            defaultextension=".battle",
            initialfile=".battle"
        )
        if not path:
            print("No file path specified. Exiting.")
            root.destroy()
            sys.exit(0)
            
        path = os.path.abspath(path)
        if path.endswith(".battle.battle"):
            path = path[:-7]
        DB_FILE = path
        os.environ["BATTLEBOTS_DB_FILE"] = path
        
        # Reset state in-place to keep references intact
        state.clear()
        state.update({
            "settings": {
                "matchDuration": 180,
                "lockRankings": False,
                "activeMatchId": None
            },
            "teams": [],
            "matches": [],
            "playoffBracket": {
                "matches": []
            },
            "timer": {
                "state": "idle",
                "duration": 180,
                "remaining": 180,
                "lastStartedAt": None,
                "countdownValue": 0
            }
        })
        save_state()
        print(f"Created new tournament and saved to: {DB_FILE}")
    
    # Clean up tkinter resource
    root.destroy()
        
    local_ip = get_local_ip()
    print("*" * 60)
    print(f"BATTLEBOTS TOURNAMENT MANAGER SERVER STARTED")
    print(f"Admin Dashboard: http://localhost:8000")
    print(f"Pit Display:     http://localhost:8000/pit")
    print(f"Audience Display:http://localhost:8000/audience")
    print("-" * 60)
    print(f"Network Access Link: http://{local_ip}:8000")
    print("*" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
