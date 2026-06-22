import os
import sys
import socket
import threading
import queue
import webbrowser
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# Ensure the directory of this file is in sys.path so we can import server.py
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import server
import uvicorn

# Determine base directory for data persistence
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class BattleBotsLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("BattleBots Tournament Manager")
        self.root.geometry("700x520")
        self.root.configure(bg="#1E1E2E")
        self.root.resizable(False, False)
        
        self.server_instance = None
        self.server_thread = None
        self.server_started = False
        self.log_queue = queue.Queue()
        
        # Modern Dark Palette (Catppuccin Mocha inspired)
        self.bg_color = "#1E1E2E"
        self.card_bg = "#252538"
        self.text_color = "#CDD6F4"
        self.accent_color = "#CBA6F7" # Lavender
        self.blue_color = "#89B4FA"   # Pastel blue
        self.green_color = "#A6E3A1"  # Pastel green
        self.red_color = "#F38BA8"    # Pastel red
        self.gray_color = "#45475A"   # Dark gray
        self.log_bg = "#11111B"       # Deep black/blue
        
        # Configure window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Initialize UI screens
        self.setup_welcome_screen()
        
        # Start log queue polling
        self.poll_logs()

    def setup_welcome_screen(self):
        self.welcome_frame = tk.Frame(self.root, bg=self.bg_color)
        self.welcome_frame.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Logo/Title
        title_label = tk.Label(
            self.welcome_frame, 
            text="BATTLEBOTS MANAGER", 
            font=("Segoe UI", 24, "bold"), 
            fg=self.accent_color, 
            bg=self.bg_color
        )
        title_label.pack(pady=(15, 5))
        
        subtitle_label = tk.Label(
            self.welcome_frame, 
            text="Load an existing tournament or create a new one to start.", 
            font=("Segoe UI", 11), 
            fg="#A6ADC8", 
            bg=self.bg_color
        )
        subtitle_label.pack(pady=(0, 30))
        
        # Buttons Container
        btn_container = tk.Frame(self.welcome_frame, bg=self.bg_color)
        btn_container.pack(fill="x", pady=5)
        
        # Load Button Card
        self.create_card_button(
            btn_container, 
            "Load Existing Tournament...", 
            "Open a previously saved .battle tournament database.", 
            self.start_load
        )
        
        # Create Button Card
        self.create_card_button(
            btn_container, 
            "Create New Tournament...", 
            "Initialize a brand new tournament (.battle) file.", 
            self.start_new
        )

    def create_card_button(self, parent, title, desc, command):
        card = tk.Frame(
            parent, 
            bg=self.card_bg, 
            bd=0, 
            highlightthickness=1, 
            highlightbackground="#313244", 
            padx=15, 
            pady=12
        )
        card.pack(fill="x", pady=6)
        
        text_frame = tk.Frame(card, bg=self.card_bg)
        text_frame.pack(side="left", fill="both", expand=True)
        
        lbl_title = tk.Label(text_frame, text=title, font=("Segoe UI", 11, "bold"), fg=self.text_color, bg=self.card_bg)
        lbl_title.pack(anchor="w")
        
        lbl_desc = tk.Label(text_frame, text=desc, font=("Segoe UI", 9), fg="#89DCEB", bg=self.card_bg)
        lbl_desc.pack(anchor="w", pady=(2, 0))
        
        btn = tk.Button(
            card, 
            text="Select", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.blue_color, 
            fg="#11111B", 
            activebackground="#B4BEFE", 
            activeforeground="#11111B",
            bd=0, 
            relief="flat", 
            padx=15, 
            pady=6,
            command=command
        )
        btn.pack(side="right", padx=(10, 0))

    def setup_dashboard_screen(self, filepath):
        self.welcome_frame.pack_forget()
        
        self.dashboard_frame = tk.Frame(self.root, bg=self.bg_color)
        self.dashboard_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Top Header Area
        header_frame = tk.Frame(self.dashboard_frame, bg=self.bg_color)
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = tk.Label(
            header_frame, 
            text="BattleBots Server Console", 
            font=("Segoe UI", 16, "bold"), 
            fg=self.accent_color, 
            bg=self.bg_color
        )
        title_label.pack(side="left")
        
        self.status_indicator = tk.Label(
            header_frame, 
            text="● STARTING", 
            font=("Segoe UI", 10, "bold"), 
            fg=self.accent_color, 
            bg=self.bg_color
        )
        self.status_indicator.pack(side="right", padx=10)
        
        # Database Info Card
        db_frame = tk.Frame(
            self.dashboard_frame, 
            bg=self.card_bg, 
            highlightthickness=1, 
            highlightbackground="#313244", 
            padx=10, 
            pady=6
        )
        db_frame.pack(fill="x", pady=(0, 10))
        
        lbl_db_title = tk.Label(db_frame, text="Active Database:", font=("Segoe UI", 9, "bold"), fg="#A6ADC8", bg=self.card_bg)
        lbl_db_title.pack(side="left")
        
        # Trim database path for display if too long
        display_path = filepath
        if len(display_path) > 75:
            display_path = "..." + display_path[-72:]
            
        lbl_db_path = tk.Label(db_frame, text=display_path, font=("Segoe UI", 9), fg=self.text_color, bg=self.card_bg)
        lbl_db_path.pack(side="left", padx=5)
        
        # Quick Actions Card
        actions_frame = tk.Frame(
            self.dashboard_frame, 
            bg=self.card_bg, 
            highlightthickness=1, 
            highlightbackground="#313244", 
            padx=15, 
            pady=10
        )
        actions_frame.pack(fill="x", pady=(0, 10))
        
        lbl_actions = tk.Label(actions_frame, text="Server Web Interfaces", font=("Segoe UI", 10, "bold"), fg=self.accent_color, bg=self.card_bg)
        lbl_actions.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        
        # Link buttons
        self.btn_admin = self.create_link_button(actions_frame, "Admin Dashboard", f"http://localhost:{self.port}", 1, 0)
        self.btn_pit = self.create_link_button(actions_frame, "Pit Display", f"http://localhost:{self.port}/pit", 1, 1)
        self.btn_audience = self.create_link_button(actions_frame, "Audience Display", f"http://localhost:{self.port}/audience", 1, 2)
        
        # Configure columns weights for equal spacing
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        actions_frame.columnconfigure(2, weight=1)
        
        # Logs Section
        log_header_frame = tk.Frame(self.dashboard_frame, bg=self.bg_color)
        log_header_frame.pack(fill="x", pady=(5, 2))
        
        lbl_logs = tk.Label(log_header_frame, text="Live Output Log", font=("Segoe UI", 10, "bold"), fg="#A6ADC8", bg=self.bg_color)
        lbl_logs.pack(side="left")
        
        # Log Text Box
        self.log_text = scrolledtext.ScrolledText(
            self.dashboard_frame, 
            bg=self.log_bg, 
            fg=self.green_color, 
            insertbackground="white", 
            font=("Consolas", 9), 
            height=14,
            bd=0,
            highlightthickness=1,
            highlightbackground="#313244"
        )
        self.log_text.pack(fill="both", expand=True)
        
        # Redirect stdout and stderr to the log text queue
        sys.stdout = StdoutRedirector(self.log_queue)
        sys.stderr = StdoutRedirector(self.log_queue)

    def create_link_button(self, parent, text, url, row, col):
        btn = tk.Button(
            parent, 
            text=text, 
            font=("Segoe UI", 9, "bold"), 
            bg=self.gray_color, 
            fg=self.text_color, 
            activebackground=self.blue_color, 
            activeforeground="#11111B",
            bd=0, 
            relief="flat", 
            padx=10, 
            pady=8,
            state="disabled", # Start disabled until server is active
            command=lambda: webbrowser.open(url)
        )
        btn.grid(row=row, column=col, padx=5, sticky="ew")
        return btn

    def start_load(self):
        path = filedialog.askopenfilename(
            title="Open Tournament File",
            filetypes=[("Battle Files", "*.battle"), ("JSON Files", "*.json"), ("All Files", "*.*")],
            defaultextension=".battle",
            initialdir=BASE_DIR
        )
        if path:
            abs_path = os.path.abspath(path)
            if abs_path.endswith(".battle.battle"):
                abs_path = abs_path[:-7]
            self.launch_server(abs_path)

    def start_new(self):
        path = filedialog.asksaveasfilename(
            title="Create New Tournament File",
            filetypes=[("Battle Files", "*.battle"), ("All Files", "*.*")],
            defaultextension=".battle",
            initialfile=".battle",
            initialdir=BASE_DIR
        )
        if path:
            abs_path = os.path.abspath(path)
            if abs_path.endswith(".battle.battle"):
                abs_path = abs_path[:-7]
            try:
                # Clean up any stale .tmp file at the target location
                tmp_path = abs_path + ".tmp"
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

                # Reset in-memory state to a clean blank tournament
                server.DB_FILE = abs_path
                os.environ["BATTLEBOTS_DB_FILE"] = abs_path
                server.state.clear()
                server.state.update(server.get_default_state())

                # Persist the clean state to the new file BEFORE starting server
                server.save_state()
                print(f"Created new tournament file: {abs_path}")

                # State is already in memory; tell launch_server not to reload from disk
                self.launch_server(abs_path, state_preloaded=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create tournament file:\n{e}")

    def terminate_process_on_port(self, port):
        try:
            pids_killed = set()
            if sys.platform.startswith('win'):
                output = subprocess.check_output("netstat -ano -p tcp", shell=True).decode('utf-8', errors='ignore')
                for line in output.splitlines():
                    if "LISTENING" in line and f":{port}" in line:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            if pid != str(os.getpid()) and pid not in pids_killed:
                                print(f"Found process {pid} listening on port {port}. Terminating...")
                                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                pids_killed.add(pid)
            else:
                try:
                    output = subprocess.check_output(f"lsof -t -i:{port}", shell=True).decode().strip()
                    for pid in output.split():
                        if pid != str(os.getpid()) and pid not in pids_killed:
                            print(f"Found process {pid} listening on port {port}. Terminating...")
                            subprocess.run(f"kill -9 {pid}", shell=True)
                            pids_killed.add(pid)
                except Exception:
                    pass
            if pids_killed:
                import time
                time.sleep(1.0)
                return True
        except Exception as e:
            print(f"Error terminating process on port {port}: {e}")
        return False

    def find_and_prepare_port(self, start_port=8000, max_attempts=10):
        for port in range(start_port, start_port + max_attempts):
            if self.is_port_open(port):
                print(f"Port {port} is occupied. Attempting to close process using it...")
                self.terminate_process_on_port(port)
            if not self.is_port_open(port):
                print(f"Selected port {port} for BattleBots Server.")
                return port
            print(f"Port {port} is still occupied. Trying next port candidate...")
        return None

    def launch_server(self, filepath, state_preloaded=False):
        # Find a free port candidate and prepare it
        self.port = self.find_and_prepare_port(8000, 10)
        if not self.port:
            messagebox.showerror(
                "No Free Port",
                "Could not find or free any port between 8000 and 8009.\n\n"
                "Please close any applications using these ports and try again."
            )
            return

        # Ensure server module points to the chosen file path
        server.DB_FILE = filepath
        os.environ["BATTLEBOTS_DB_FILE"] = filepath

        # Load from file only when the caller hasn't already set up the state
        # (start_new sets state before calling; start_default/start_load do not)
        if not state_preloaded:
            server.load_state()
        print(f"Server starting with DB: {filepath} on port {self.port}")
        print(f"Teams in memory: {len(server.state.get('teams', []))}, "
              f"Matches: {len(server.state.get('matches', []))}")
        
        self.setup_dashboard_screen(filepath)
        
        # Start uvicorn server in a daemon thread
        def run_uvicorn():
            try:
                config = uvicorn.Config(
                    server.app, 
                    host="0.0.0.0", 
                    port=self.port, 
                    log_level="info", 
                    ws_max_size=16777216,
                    log_config=None
                )
                self.server_instance = uvicorn.Server(config)
                self.server_instance.run()
            except Exception as e:
                print(f"\nERROR: Server failed to start: {e}\n")
        
        self.server_thread = threading.Thread(target=run_uvicorn, daemon=True)
        self.server_thread.start()
        
        # Start checking if server is active
        self.check_server_active(0)

    def check_server_active(self, attempts):
        # Attempt to connect to port self.port to see if server started
        if self.is_port_open(self.port):
            self.server_started = True
            self.status_indicator.config(text="● RUNNING", fg=self.green_color)
            
            # Enable link buttons
            self.btn_admin.config(state="normal", bg=self.blue_color, fg="#11111B")
            self.btn_pit.config(state="normal")
            self.btn_audience.config(state="normal")
            
            # Auto-open Admin dashboard in default browser
            webbrowser.open(f"http://localhost:{self.port}")
            print(f"\nBattleBots Server is active on port {self.port}. Opening dashboard...\n")
        else:
            if attempts < 20: # 10 seconds timeout
                self.root.after(500, lambda: self.check_server_active(attempts + 1))
            else:
                self.status_indicator.config(text="● TIMEOUT / ERROR", fg=self.red_color)
                print(f"\nERROR: Timeout waiting for server to bind on port {self.port}.\nPlease verify if another app is already using port {self.port}.\n")

    def is_port_open(self, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                s.connect(("127.0.0.1", port))
                return True
        except Exception:
            return False

    def poll_logs(self):
        # Read from log queue and insert into ScrolledText
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                if hasattr(self, 'log_text') and self.log_text.winfo_exists():
                    self.log_text.insert(tk.END, msg)
                    self.log_text.see(tk.END)
            except queue.Empty:
                break
        self.root.after(100, self.poll_logs)

    def on_close(self):
        # Gracefully shut down server and exit
        if self.server_instance:
            print("Stopping uvicorn server...")
            self.server_instance.should_exit = True
            try:
                if hasattr(self.server_instance, 'servers'):
                    for s_obj in self.server_instance.servers:
                        for sock in s_obj.sockets:
                            sock.close()
            except Exception:
                pass
            
        self.root.destroy()
        os._exit(0)

class StdoutRedirector:
    def __init__(self, queue):
        self.queue = queue

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass

    def isatty(self):
        return False

if __name__ == "__main__":
    root = tk.Tk()
    app = BattleBotsLauncher(root)
    root.mainloop()
