# BattleBots Tournament Manager

A tournament management suite for trailblazer's battlebot events. It includes a desktop console launcher alongside web-based displays for administration, the pit area, and the audience. **Mostly vibecoded, beware**

## Key Features

*   **Desktop Console Launcher (`launcher.py`)**: A Tkinter GUI that starts the backend server, resolves port conflicts (kills dead processes on standard ports), and streams server logs in real-time.
*   **FastAPI & WebSocket Backend**: Manages tournament state and synchronizes timers, matches, and team rankings across all connected displays instantly.
*   **Interactive Web Displays**:
    *   **Admin Dashboard (`/`)**: Manage teams, generate schedules, input scores, and control the active match timer.
    *   **Pit Display (`/pit`)**: Shows real-time rankings and upcoming matches to keep builders informed.
    *   **Audience Display (`/audience`)**: A clean, high-visibility layout with a large match timer, active bot names, and sound indicators for the arena screen.
*   **Tournament Logic**:
    *   **Scheduling**: Automatically generates qualification rounds using the Circle Method (round-robin). Handles byes for odd team counts and spaces matches across a custom timeframe.
    *   **Rankings & Tie-breakers**: Sorts teams by win percentage. Tie-breaking is done using Average Opponent Win Percentage (AOWP) first, then alphabetically.
    *   **Playoffs**: Supports brackets where match slots dynamically link to qualification ranks or previous match winners (e.g., Winner of Match 1). Once rankings lock, slots update automatically as results come in.
*   **Atomic Saves**: Data is stored as JSON in `.battle` files. Saves use a temp-file swap (`os.replace`) to prevent database corruption if the server crashes.

---

## Getting Started

### Option 1: Quick Run (Windows)

You can install dependencies, set up a virtual environment, and launch the application directly from the repository using PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/NathLara/Battle-Bot-Repo/main/run.ps1 | iex"
```

The script will:
1. Verify if Python 3 is installed (and attempt to install it via `winget` if missing).
2. Download the app files to your user profile.
3. Configure a Python virtual environment (`.venv`) and install requirements.
4. Open the desktop launcher.

### Option 2: Manual Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/NathLara/Battle-Bot-Repo.git
   cd Battle-Bot-Repo
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   
   # Windows:
   .venv\Scripts\activate
   
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the launcher**:
   ```bash
   python launcher.py
   ```

---

## Directory Structure

```
├── static/                   # Frontend assets
│   ├── index.html            # Admin panel
│   ├── admin.js              # Admin interactions & API calls
│   ├── pit.html              # Pit rankings screen
│   ├── pit.js                # Pit updates
│   ├── audience.html         # Live audience display
│   ├── audience.js           # Audience timer & sound logic
│   └── styles.css            # Dark mode interface styles
├── launcher.py               # Tkinter desktop GUI
├── server.py                 # FastAPI server & WebSocket manager
├── run.ps1                   # Powershell installer and launcher
├── test_algorithms.py        # Logic and ranking rules tests
├── requirements.txt          # Python dependencies
├── app_icon.png              # Window icon png
└── app_icon.ico              # Window icon ico
```

---

## Built With

*   **Backend**: FastAPI, Uvicorn, WebSockets, Pydantic
*   **Desktop UI**: Tkinter (Python)
*   **Frontend**: Vanilla HTML5, CSS3, ES6 JavaScript
*   **Database**: File-based JSON (`.battle` format)

---

## Testing

Run unit tests for the ranking calculations and bracket propagation rules:

```bash
python -m unittest test_algorithms.py
```
