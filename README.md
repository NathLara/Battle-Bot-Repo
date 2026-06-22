# 🤖 BattleBots Tournament Manager

A premium, modern tournament management suite designed for combat robotics/BattleBots competitions. It provides a multi-screen setup comprising a desktop control console, an interactive admin panel, real-time pit displays, and high-visibility audience views.

## 🌟 Key Features

*   **Modern Desktop Launcher (`launcher.py`)**: Built with a sleek dark-theme console UI (inspired by the *Catppuccin Mocha* palette). It manages system ports, terminates zombie/hanging processes automatically, and hosts direct launcher links for all screens.
*   **Asynchronous FastAPI Backend**: Real-time synchronization of tournament states, timers, and rankings powered by WebSockets.
*   **Dynamic Views**:
    *   **Admin Dashboard (`/`)**: Main console to register teams, generate and reorder match schedules, update match outcomes, and run the active match timer.
    *   **Pit Display (`/pit`)**: Highlights live-updated team rankings, win/loss stats, and upcoming matchups.
    *   **Audience Display (`/audience`)**: A high-visibility full-screen view featuring an active match timer (with audio/visual indicators), team labels, and live status updates.
*   **Advanced Tournament Algorithms**:
    *   *Round-Robin Generator*: Generates qualification rounds automatically using the **Circle Method**, handling bye matches for odd team counts and scheduling around custom time blocks.
    *   *Sophisticated Tie-Breakers*: Teams are ranked by win percentage. Ties are resolved dynamically using **Average Opponent Win Percentage (AOWP)**, followed by alphabetical order.
    *   *Playoff Bracket Propagation*: Supports custom playoff slots linked to qualification ranks (e.g., Rank 1 vs Rank 4) or preceding match winners (e.g., Winner of SF1 vs Winner of SF2). Winners propagate automatically downstream once rankings are locked.
*   **Atomic Database Persistence**: State is saved to standard `.battle` JSON database files. To prevent data corruption, updates are written to temporary files and atomically swapped (`os.replace`).

---

## 🚀 Getting Started

### Option 1: One-Click Execution (Windows Power Users)

Any Windows system with internet access can install dependencies, set up a virtual environment, and launch the application directly from the GitHub repository using a single PowerShell command:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/NathLara/Battle-Bot-Repo/main/run.ps1 | iex"
```

*What this script does:*
1. Checks for Python 3 and attempts to install it via Windows Package Manager (`winget`) if missing.
2. Downloads the latest code files from the GitHub repository.
3. Automatically sets up a local virtual environment (`.venv`) and installs the required packages.
4. Boots the desktop interface (`launcher.py`).

### Option 2: Manual Installation & Execution

For manual setups, developers, or non-Windows users:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/NathLara/Battle-Bot-Repo.git
   cd Battle-Bot-Repo
   ```

2. **Set up a Virtual Environment**:
   ```bash
   python -m venv .venv
   
   # On Windows:
   .venv\Scripts\activate
   
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the Application**:
   ```bash
   python launcher.py
   ```

---

## 📁 Repository Structure

```
├── static/                   # Client-side web applications
│   ├── index.html            # Admin Dashboard HTML
│   ├── admin.js              # Admin UI logic
│   ├── pit.html              # Pit Display HTML
│   ├── pit.js                # Pit UI logic
│   ├── audience.html         # Audience Display HTML
│   ├── audience.js           # Audience UI logic
│   └── styles.css            # Dark/vibrant styling suite
├── launcher.py               # Desktop GUI server console (Tkinter)
├── server.py                 # FastAPI & WebSocket server
├── run.ps1                   # Bootstrap installer/launcher script
├── test_algorithms.py        # Unit tests for ranking & bracket rules
├── requirements.txt          # Python package requirements
├── app_icon.png              # Application logo
└── app_icon.ico              # Windows executable icon
```

---

## 🛠️ Technology Stack

*   **Backend**: FastAPI, Uvicorn, Websockets, Pydantic (Python 3.8+)
*   **Desktop Interface**: Tkinter, Python socket & multithreading, subprocess
*   **Frontend**: Vanilla HTML5, CSS3, ES6 JavaScript
*   **Data Store**: Atomically swapped JSON (`.battle`) database

---

## 🧪 Running Unit Tests

The algorithms for the tournament rankings and bracket winner propagation are covered by a suite of unit tests. You can run them locally using:

```bash
python -m unittest test_algorithms.py
```
