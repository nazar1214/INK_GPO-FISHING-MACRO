import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import sys
import ctypes

# Third-party imports
import keyboard
import mss
import numpy as np
import win32api
import win32con
from pynput import mouse as pynput_mouse
from pynput import keyboard as pynput_keyboard

# ==========================================
# Constants
# ==========================================
COLOR_TARGET_BLUE = (255, 170, 85)   # #55aaff (BGR)
COLOR_DARK = (25, 25, 25)            # #191919 (BGR)
COLOR_WHITE = (255, 255, 255)        # #ffffff (BGR)

class ModernGPOBot:
    def __init__(self, root):
        self.root = root
        self.root.title('INK_GPO FISHING BOT')
        self.root.attributes('-topmost', True)
        self.root.protocol('WM_DELETE_WINDOW', self.exit_app)
        
        self.colors = {
            'bg': '#1e1e1e', 'panel': '#252526', 'fg': '#cccccc',
            'accent': '#007acc', 'accent_hover': '#0098ff',
            'danger': '#f44336', 'success': '#4caf50', 'warning': '#ff9800'
        }
        self.root.configure(bg=self.colors['bg'])

        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass

        # State
        self.main_loop_active = False
        self.overlay_active = False
        self.overlay_window = None
        self.recording_hotkey = None
        self.is_clicking = False
        
        # Flags
        self.needs_bait_reselect = True 
        
        # Counters
        self.purchase_counter = 0
        self.craft_counter = 0
        self.fish_catch_counter = 0
        
        self.dpi_scale = self.get_dpi_scale()
        
        # Overlay Geometry
        base_width = 172
        base_height = 495
        self.overlay_area = {
            'x': int(100 * self.dpi_scale),
            'y': int(100 * self.dpi_scale),
            'width': int(base_width * self.dpi_scale),
            'height': int(base_height * self.dpi_scale)
        }
        
        self.previous_error = 0
        
        # Coordinates storage
        self.point_coords = {1: None, 2: None, 3: None} 
        self.craft_coords = {'craft_btn': None, 'legendary': None, 'rare': None, 'common': None, 'water': None}
        self.fruit_coords = {'fruit_slot': None, 'bait_slot': None}
        
        self.hotkeys = {'toggle_loop': 'f1', 'toggle_overlay': 'f2', 'exit': 'f3'}

        self.setup_styles()
        self.setup_ui()
        self.register_hotkeys()
        self.root.update_idletasks()
        self.root.minsize(450, 950)

    def get_dpi_scale(self):
        try: return self.root.winfo_fpixels('1i') / 96.0
        except: return 1.0

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('Card.TFrame', background=self.colors['panel'], relief='flat')
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'], font=('Segoe UI', 10))
        style.configure('Card.TLabel', background=self.colors['panel'], foreground=self.colors['fg'], font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 18, 'bold'), foreground=self.colors['accent'])
        style.configure('SubHeader.TLabel', background=self.colors['panel'], font=('Segoe UI', 11, 'bold'), foreground=self.colors['fg'])
        style.configure('TButton', background=self.colors['panel'], foreground=self.colors['fg'], borderwidth=0, font=('Segoe UI', 9))
        style.map('TButton', background=[('active', self.colors['accent'])], foreground=[('active', 'white')])
        style.configure('Accent.TButton', background=self.colors['accent'], foreground='white', font=('Segoe UI', 9, 'bold'))
        style.map('Accent.TButton', background=[('active', self.colors['accent_hover'])])

    def setup_ui(self):
        canvas = tk.Canvas(self.root, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # --- Header ---
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill='x', pady=(15, 15), padx=15)
        ttk.Label(header_frame, text='INK_GPO FISHING BOT', style='Header.TLabel').pack(side='left')
        self.status_indicator = tk.Label(header_frame, text="STOPPED", bg=self.colors['danger'], fg='white', font=('Segoe UI', 8, 'bold'), padx=8, pady=2)
        self.status_indicator.pack(side='right')

        status_frame = ttk.Frame(scrollable_frame)
        status_frame.pack(fill='x', pady=(0, 10), padx=15)
        self.overlay_label = ttk.Label(status_frame, text='Overlay: HIDDEN', foreground='#666666')
        self.overlay_label.pack(side='right')

        # --- Cards ---
        self.create_card(scrollable_frame, "Auto Purchase", self.setup_auto_buy_content)
        self.create_card(scrollable_frame, "Auto Crafting", self.setup_auto_craft_content)
        self.create_card(scrollable_frame, "Fruit Storage & Bait", self.setup_fruit_bait_content)
        self.create_card(scrollable_frame, "Mechanics & Timing", self.setup_mechanics_content)
        self.create_card(scrollable_frame, "Hotkeys", self.setup_hotkeys_content)

        self.msg_label = ttk.Label(scrollable_frame, text="Ready.", foreground=self.colors['accent'])
        self.msg_label.pack(side='bottom', fill='x', pady=10, padx=15)
        
        self.root.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def create_card(self, parent, title, content_func):
        card = ttk.Frame(parent, style='Card.TFrame', padding=10)
        card.pack(fill='x', pady=5, padx=15)
        ttk.Label(card, text=title, style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))
        content_func(card)

    # ================= UI SECTIONS =================

    def setup_auto_buy_content(self, parent):
        self.auto_purchase_var = tk.BooleanVar(value=False) # Default False
        cb = tk.Checkbutton(parent, text="Enable Auto Buy", variable=self.auto_purchase_var,
                            bg=self.colors['panel'], fg=self.colors['fg'],
                            selectcolor=self.colors['bg'], activebackground=self.colors['panel'], activeforeground='white')
        cb.pack(anchor='w', pady=(0, 5))

        grid = ttk.Frame(parent, style='Card.TFrame')
        grid.pack(fill='x')
        ttk.Label(grid, text="Amount:", style='Card.TLabel').grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.amount_var = tk.IntVar(value=10)
        tk.Spinbox(grid, from_=0, to=9999, textvariable=self.amount_var, width=8, bg=self.colors['bg'], fg='white', relief='flat').grid(row=0, column=1, pady=2)
        ttk.Label(grid, text="Loops/Buy:", style='Card.TLabel').grid(row=0, column=2, sticky='w', padx=15, pady=2)
        self.loops_var = tk.IntVar(value=15)
        tk.Spinbox(grid, from_=1, to=9999, textvariable=self.loops_var, width=8, bg=self.colors['bg'], fg='white', relief='flat').grid(row=0, column=3, pady=2)
        
        # SPEED CONTROL
        ttk.Label(grid, text="Action Delay (s):", style='Card.TLabel').grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.purchase_speed_var = tk.DoubleVar(value=0.5)
        tk.Spinbox(grid, from_=0.1, to=5.0, increment=0.1, textvariable=self.purchase_speed_var, width=8, bg=self.colors['bg'], fg='white', relief='flat').grid(row=1, column=1, pady=2)

        btn_grid = ttk.Frame(parent, style='Card.TFrame')
        btn_grid.pack(fill='x', pady=5)
        self.point_buttons = {}
        
        # Points 1, 2, 3
        for i in range(1, 4):
            r, c = divmod(i-1, 2)
            btn = ttk.Button(btn_grid, text=f"Set Pt {i}", command=lambda x=i: self.capture_mouse_click(x, 'buy'))
            btn.grid(row=r, column=c, sticky='ew', padx=2, pady=2)
            btn_grid.columnconfigure(c, weight=1)
            self.point_buttons[i] = btn
            
        # UNIVERSAL WATER POINT
        self.water_btn_buy = ttk.Button(btn_grid, text="Set Water Pt (Univ)", command=lambda: self.capture_mouse_click('water', 'craft'))
        self.water_btn_buy.grid(row=1, column=1, sticky='ew', padx=2, pady=2)

    def setup_auto_craft_content(self, parent):
        self.auto_craft_var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(parent, text="Enable Auto Crafting", variable=self.auto_craft_var,
                            bg=self.colors['panel'], fg=self.colors['fg'],
                            selectcolor=self.colors['bg'], activebackground=self.colors['panel'], activeforeground='white')
        cb.pack(anchor='w', pady=(0, 5))

        settings_grid = ttk.Frame(parent, style='Card.TFrame')
        settings_grid.pack(fill='x', pady=5)

        ttk.Label(settings_grid, text="Craft Every:", style='Card.TLabel').grid(row=0, column=0, sticky='w')
        self.craft_loop_var = tk.IntVar(value=1)
        tk.Spinbox(settings_grid, from_=1, to=9999, textvariable=self.craft_loop_var, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=0, column=1, padx=5)
        ttk.Label(settings_grid, text="Fish", style='Card.TLabel').grid(row=0, column=2, sticky='w', padx=(0, 15))

        # UPDATED DEFAULTS: Menu Delay 0.1, Click Speed 0.01
        ttk.Label(settings_grid, text="Menu Delay (s):", style='Card.TLabel').grid(row=1, column=0, sticky='w')
        self.craft_menu_delay_var = tk.DoubleVar(value=0.1)
        tk.Spinbox(settings_grid, from_=0.1, to=5.0, increment=0.1, textvariable=self.craft_menu_delay_var, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=1, column=1, padx=5)

        ttk.Label(settings_grid, text="Click Speed (s):", style='Card.TLabel').grid(row=1, column=2, sticky='w')
        self.craft_speed_var = tk.DoubleVar(value=0.01)
        tk.Spinbox(settings_grid, from_=0.01, to=2.0, increment=0.01, textvariable=self.craft_speed_var, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=1, column=3, padx=5)

        self.craft_btns = {} 
        self.craft_btns['water'] = ttk.Button(settings_grid, text="Set Water Pt", command=lambda: self.capture_mouse_click('water', 'craft'))
        self.craft_btns['water'].grid(row=2, column=0, columnspan=2, padx=0, pady=5, sticky='w')

        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)

        f_top = ttk.Frame(parent, style='Card.TFrame')
        f_top.pack(fill='x', pady=2)
        self.craft_btns['craft_btn'] = ttk.Button(f_top, text="Set Main 'Craft' Button", command=lambda: self.capture_mouse_click('craft_btn', 'craft'))
        self.craft_btns['craft_btn'].pack(fill='x')

        grid = ttk.Frame(parent, style='Card.TFrame')
        grid.pack(fill='x', pady=5)
        
        self.legendary_count = tk.IntVar(value=0)
        ttk.Label(grid, text="Legendary", style='Card.TLabel', foreground='#ffa500').grid(row=1, column=0, sticky='w', pady=2)
        tk.Spinbox(grid, from_=0, to=999, textvariable=self.legendary_count, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=1, column=1, padx=5)
        self.craft_btns['legendary'] = ttk.Button(grid, text="Set Pos", width=8, command=lambda: self.capture_mouse_click('legendary', 'craft'))
        self.craft_btns['legendary'].grid(row=1, column=2)

        self.rare_count = tk.IntVar(value=0)
        ttk.Label(grid, text="Rare", style='Card.TLabel', foreground='#add8e6').grid(row=2, column=0, sticky='w', pady=2)
        tk.Spinbox(grid, from_=0, to=999, textvariable=self.rare_count, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=2, column=1, padx=5)
        self.craft_btns['rare'] = ttk.Button(grid, text="Set Pos", width=8, command=lambda: self.capture_mouse_click('rare', 'craft'))
        self.craft_btns['rare'].grid(row=2, column=2)

        self.common_count = tk.IntVar(value=20)
        ttk.Label(grid, text="Common", style='Card.TLabel', foreground='white').grid(row=3, column=0, sticky='w', pady=2)
        tk.Spinbox(grid, from_=0, to=999, textvariable=self.common_count, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=3, column=1, padx=5)
        self.craft_btns['common'] = ttk.Button(grid, text="Set Pos", width=8, command=lambda: self.capture_mouse_click('common', 'craft'))
        self.craft_btns['common'].grid(row=3, column=2)

    def setup_fruit_bait_content(self, parent):
        # --- Fruit Storage ---
        self.fruit_storage_var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(parent, text="Enable Fruit Storage", variable=self.fruit_storage_var,
                            bg=self.colors['panel'], fg=self.colors['fg'],
                            selectcolor=self.colors['bg'], activebackground=self.colors['panel'], activeforeground='white')
        cb.pack(anchor='w', pady=(0, 2))

        # --- Auto Bait ---
        self.auto_bait_var = tk.BooleanVar(value=False)
        cb_bait = tk.Checkbutton(parent, text="Auto Select Bait (Universal)", variable=self.auto_bait_var,
                            bg=self.colors['panel'], fg=self.colors['fg'],
                            selectcolor=self.colors['bg'], activebackground=self.colors['panel'], activeforeground='white')
        cb_bait.pack(anchor='w', pady=(0, 5))

        grid = ttk.Frame(parent, style='Card.TFrame')
        grid.pack(fill='x')
        
        # Keys Row 1
        ttk.Label(grid, text="Fruit Key:", style='Card.TLabel').grid(row=0, column=0, sticky='w')
        self.fruit_key_var = tk.StringVar(value="3")
        tk.Entry(grid, textvariable=self.fruit_key_var, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(grid, text="Check Every:", style='Card.TLabel').grid(row=0, column=2, sticky='w', padx=10)
        self.fruit_check_loop_var = tk.IntVar(value=1)
        tk.Spinbox(grid, from_=1, to=999, textvariable=self.fruit_check_loop_var, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=0, column=3, padx=5)

        # Keys Row 2 (Rod Logic)
        ttk.Label(grid, text="Rod Key:", style='Card.TLabel').grid(row=1, column=0, sticky='w', pady=5)
        self.rod_key_var = tk.StringVar(value="1")
        tk.Entry(grid, textvariable=self.rod_key_var, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=1, column=1, padx=5)
        
        ttk.Label(grid, text="Not Rod:", style='Card.TLabel').grid(row=1, column=2, sticky='w', padx=10)
        self.non_rod_key_var = tk.StringVar(value="2")
        tk.Entry(grid, textvariable=self.non_rod_key_var, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=1, column=3, padx=5)

        # UPDATED DEFAULT: Action Speed 0.30
        ttk.Label(grid, text="Action Speed (s):", style='Card.TLabel').grid(row=2, column=0, sticky='w', pady=5)
        self.fruit_speed_var = tk.DoubleVar(value=0.30)
        tk.Spinbox(grid, from_=0.05, to=2.0, increment=0.05, textvariable=self.fruit_speed_var, width=5, bg=self.colors['bg'], fg='white', relief='flat').grid(row=2, column=1, padx=5)

        # Buttons
        btn_grid = ttk.Frame(parent, style='Card.TFrame')
        btn_grid.pack(fill='x', pady=5)
        
        self.fruit_btns = {}
        self.fruit_btns['fruit_slot'] = ttk.Button(btn_grid, text="Set Fruit Point", command=lambda: self.capture_mouse_click('fruit_slot', 'fruit'))
        self.fruit_btns['fruit_slot'].pack(side='left', fill='x', expand=True, padx=2)
        
        self.fruit_btns['bait_slot'] = ttk.Button(btn_grid, text="Set Bait Point", command=lambda: self.capture_mouse_click('bait_slot', 'fruit'))
        self.fruit_btns['bait_slot'].pack(side='left', fill='x', expand=True, padx=2)

    def setup_mechanics_content(self, parent):
        grid = ttk.Frame(parent, style='Card.TFrame')
        grid.pack(fill='x')
        
        # PID Settings
        ttk.Label(grid, text="Kp (Strength):", style='Card.TLabel').grid(row=0, column=0, sticky='w', padx=5)
        self.kp_var = tk.DoubleVar(value=0.10)
        tk.Scale(grid, from_=0.0, to=2.0, resolution=0.01, variable=self.kp_var, orient='horizontal', bg=self.colors['panel'], fg='white', highlightthickness=0, length=100).grid(row=0, column=1)
        
        ttk.Label(grid, text="Kd (Stability):", style='Card.TLabel').grid(row=1, column=0, sticky='w', padx=5)
        self.kd_var = tk.DoubleVar(value=0.50)
        tk.Scale(grid, from_=0.0, to=2.0, resolution=0.01, variable=self.kd_var, orient='horizontal', bg=self.colors['panel'], fg='white', highlightthickness=0, length=100).grid(row=1, column=1)
        
        # UPDATED DEFAULTS: Rod Reset 0, Timeout 10
        ttk.Label(grid, text="Rod Reset (s):", style='Card.TLabel').grid(row=0, column=2, sticky='w', padx=15)
        self.rod_reset_var = tk.DoubleVar(value=0.0)
        tk.Spinbox(grid, from_=0.0, to=10.0, increment=0.1, textvariable=self.rod_reset_var, width=6, bg=self.colors['bg'], fg='white', relief='flat').grid(row=0, column=3)
        
        ttk.Label(grid, text="Timeout (s):", style='Card.TLabel').grid(row=1, column=2, sticky='w', padx=15)
        self.timeout_var = tk.DoubleVar(value=10.0)
        tk.Spinbox(grid, from_=1.0, to=120.0, increment=1.0, textvariable=self.timeout_var, width=6, bg=self.colors['bg'], fg='white', relief='flat').grid(row=1, column=3)

        # UPDATED DEFAULTS: Switch Delay 0.1, Cast Hold 0.1
        ttk.Label(grid, text="Switch Delay (s):", style='Card.TLabel').grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.rod_switch_delay_var = tk.DoubleVar(value=0.10)
        tk.Spinbox(grid, from_=0.05, to=2.0, increment=0.05, textvariable=self.rod_switch_delay_var, width=6, bg=self.colors['bg'], fg='white', relief='flat').grid(row=2, column=1, sticky='w')

        ttk.Label(grid, text="Cast Hold (s):", style='Card.TLabel').grid(row=2, column=2, sticky='w', padx=15, pady=5)
        self.cast_duration_var = tk.DoubleVar(value=0.1)
        tk.Spinbox(grid, from_=0.1, to=5.0, increment=0.1, textvariable=self.cast_duration_var, width=6, bg=self.colors['bg'], fg='white', relief='flat').grid(row=2, column=3, sticky='w')

        # === NEW TOGGLE FOR ROD SWITCHING ===
        self.always_rod_var = tk.BooleanVar(value=False)
        cb_rod = tk.Checkbutton(parent, text="Always Rod Mode (No Switching)", variable=self.always_rod_var,
                            bg=self.colors['panel'], fg=self.colors['fg'],
                            selectcolor=self.colors['bg'], activebackground=self.colors['panel'], activeforeground='white')
        cb_rod.pack(anchor='w', pady=(5, 0))

    def setup_hotkeys_content(self, parent):
        for i, (key_id, label_text) in enumerate([('toggle_loop', 'Start/Stop'), ('toggle_overlay', 'Overlay'), ('exit', 'Exit App')]):
            f = ttk.Frame(parent, style='Card.TFrame')
            f.pack(fill='x', pady=1)
            ttk.Label(f, text=label_text, style='Card.TLabel', width=15).pack(side='left')
            lbl = tk.Label(f, text=self.hotkeys[key_id].upper(), bg=self.colors['bg'], fg='white', width=10, relief='flat')
            lbl.pack(side='left', padx=10)
            ttk.Button(f, text="Bind", width=6, command=lambda k=key_id, l=lbl: self.start_rebind(k, l)).pack(side='right')

    # ================= Click & Input Logic =================

    def capture_mouse_click(self, key_id, mode):
        self.msg_label.config(text=f"Click to set {key_id}...", foreground=self.colors['accent'])
        def on_click(x, y, button, pressed):
            if pressed:
                if mode == 'buy':
                    self.point_coords[key_id] = (x, y)
                    self.root.after(0, lambda: self.finish_capture_buy(key_id))
                elif mode == 'craft':
                    self.craft_coords[key_id] = (x, y)
                    self.root.after(0, lambda: self.finish_capture_craft(key_id))
                elif mode == 'fruit':
                    self.fruit_coords[key_id] = (x, y)
                    self.root.after(0, lambda: self.finish_capture_fruit(key_id))
                return False
        pynput_mouse.Listener(on_click=on_click).start()

    def finish_capture_buy(self, idx):
        self.point_buttons[idx].config(text=f"Pt {idx} Set", style='Accent.TButton')
        self.msg_label.config(text=f"Buy Point {idx} set.", foreground=self.colors['success'])

    def finish_capture_craft(self, key):
        if key in self.craft_btns:
            txt = "Set"
            if key in ['legendary', 'rare', 'common']: txt = "Pos Set"
            if key == 'water': txt = "Water Set"
            self.craft_btns[key].config(text=txt, style='Accent.TButton')
        
        if key == 'water' and hasattr(self, 'water_btn_buy'):
            self.water_btn_buy.config(text="Water Set", style='Accent.TButton')
            
        self.msg_label.config(text=f"Craft Point {key} set.", foreground=self.colors['success'])

    def finish_capture_fruit(self, key):
        if key in self.fruit_btns:
            self.fruit_btns[key].config(text="Set", style='Accent.TButton')
        self.msg_label.config(text=f"Fruit Point {key} set.", foreground=self.colors['success'])

    def start_rebind(self, key_id, label_widget):
        self.msg_label.config(text=f"Press key for {key_id}...", foreground=self.colors['warning'])
        self.recording_hotkey = (key_id, label_widget)
        self.rebind_listener = pynput_keyboard.Listener(on_press=self.on_rebind_press)
        self.rebind_listener.start()

    def on_rebind_press(self, key):
        try:
            k_str = key.char if hasattr(key, 'char') else str(key).replace('Key.', '')
            action, label = self.recording_hotkey
            self.hotkeys[action] = k_str
            self.root.after(0, lambda: label.config(text=k_str.upper()))
            self.root.after(0, lambda: self.msg_label.config(text=f"Bound {action} to {k_str}", foreground=self.colors['success']))
            self.root.after(0, self.register_hotkeys)
            return False
        except: return False

    def register_hotkeys(self):
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.hotkeys['toggle_loop'], self.toggle_main_loop)
            keyboard.add_hotkey(self.hotkeys['toggle_overlay'], self.toggle_overlay)
            keyboard.add_hotkey(self.hotkeys['exit'], self.exit_app)
        except: pass

    # ================= Overlay Logic =================

    def toggle_overlay(self):
        if self.overlay_active:
            if self.overlay_window: self.overlay_window.destroy()
            self.overlay_active = False
            self.overlay_label.config(text="Overlay: HIDDEN", foreground='#666666')
        else:
            self.overlay_active = True
            self.overlay_label.config(text="Overlay: VISIBLE", foreground=self.colors['accent'])
            self.create_overlay()

    def create_overlay(self):
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.attributes('-topmost', True, '-alpha', 0.5)
        self.overlay_window.overrideredirect(True)
        self.overlay_window.configure(bg='red')
        g = f"{self.overlay_area['width']}x{self.overlay_area['height']}+{self.overlay_area['x']}+{self.overlay_area['y']}"
        self.overlay_window.geometry(g)
        self.overlay_window.bind('<ButtonPress-1>', self._overlay_start_drag)
        self.overlay_window.bind('<B1-Motion>', self._overlay_on_drag)
        self.overlay_window.bind('<ButtonRelease-1>', self._overlay_stop_drag)
        self.overlay_window.bind('<Motion>', self._overlay_update_cursor)
        self._drag_data = {"x": 0, "y": 0, "mode": None}

    def _get_resize_mode(self, x, y, w, h):
        edge_size = 15
        if x < edge_size and y < edge_size: return 'nw'
        if x > w - edge_size and y > h - edge_size: return 'se'
        if x < edge_size and y > h - edge_size: return 'sw'
        if x > w - edge_size and y < edge_size: return 'ne'
        return 'move'

    def _overlay_update_cursor(self, event):
        w = self.overlay_window.winfo_width()
        h = self.overlay_window.winfo_height()
        mode = self._get_resize_mode(event.x, event.y, w, h)
        cursor_map = {'nw': 'size_nw_se', 'se': 'size_nw_se', 'sw': 'size_ne_sw', 'ne': 'size_ne_sw', 'move': 'fleur'}
        self.overlay_window.config(cursor=cursor_map.get(mode, 'arrow'))

    def _overlay_start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        w = self.overlay_window.winfo_width()
        h = self.overlay_window.winfo_height()
        self._drag_data["mode"] = self._get_resize_mode(event.x, event.y, w, h)

    def _overlay_on_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        cur_x = self.overlay_window.winfo_x()
        cur_y = self.overlay_window.winfo_y()
        cur_w = self.overlay_window.winfo_width()
        cur_h = self.overlay_window.winfo_height()
        mode = self._drag_data["mode"]

        if mode == 'move':
            new_x = cur_x + dx
            new_y = cur_y + dy
            self.overlay_window.geometry(f"{cur_w}x{cur_h}+{new_x}+{new_y}")
            self.overlay_area['x'] = new_x
            self.overlay_area['y'] = new_y
        elif mode == 'se':
            new_w = max(50, cur_w + dx)
            new_h = max(50, cur_h + dy)
            self.overlay_window.geometry(f"{new_w}x{new_h}+{cur_x}+{cur_y}")
            self._drag_data["x"] = event.x
            self._drag_data["y"] = event.y
            self.overlay_area['width'] = new_w
            self.overlay_area['height'] = new_h

    def _overlay_stop_drag(self, event):
        self._drag_data["mode"] = None

    # ================= Automation Primitives =================

    def click_at(self, coords):
        if not coords: return
        try:
            x, y = int(coords[0]), int(coords[1])
            win32api.SetCursorPos((x, y))
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 1, 1, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -1, -1, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except: pass

    def move_and_wiggle(self, coords):
        if not coords: return
        try:
            x, y = int(coords[0]), int(coords[1])
            win32api.SetCursorPos((x, y))
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 1, 1, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -1, -1, 0, 0)
        except: pass

    def press_key(self, k, duration=0.3):
        try:
            vk = win32api.VkKeyScan(k)
            scan = win32api.MapVirtualKey(vk & 0xFF, 0)
            win32api.keybd_event(vk, scan, 0, 0)
            time.sleep(duration)
            win32api.keybd_event(vk, scan, win32con.KEYEVENTF_KEYUP, 0)
        except:
            keyboard.press(k)
            time.sleep(duration)
            keyboard.release(k)

    def type_text(self, text):
        for char in str(text):
            self.press_key(char, 0.02)
            time.sleep(0.02)

    def force_equip_rod(self):
        try:
            rod = self.rod_key_var.get()
            
            # --- MODIFIED LOGIC: TOGGLEABLE SWITCHING ---
            if self.always_rod_var.get():
                # Just press rod key to ensure equipped, no switching
                self.press_key(rod, 0.05)
            else:
                # Classic Switching
                not_rod = self.non_rod_key_var.get()
                delay = self.rod_switch_delay_var.get()
                self.press_key(not_rod, 0.05)
                time.sleep(delay)
                self.press_key(rod, 0.05)
                time.sleep(delay + 0.1)
        except: pass

    def cast_line(self):
        print("Casting Phase...")
        if self.auto_bait_var.get() and self.needs_bait_reselect:
            print("Auto selecting bait...")
            self.select_bait()
            self.needs_bait_reselect = False 
        
        # UNIVERSAL WATER POINT
        if self.craft_coords['water']:
            self.move_and_wiggle(self.craft_coords['water'])
            time.sleep(0.2)
        
        hold_time = self.cast_duration_var.get()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(hold_time)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.is_clicking = False

    def run_auto_purchase(self):
        print("Starting Auto Purchase (Asphalt Logic)...")
        pts = self.point_coords
        water_pt = self.craft_coords['water']
        
        # Check Points
        if not all([pts[1], pts[2], pts[3], water_pt]): 
            print("ERROR: Missing points for auto purchase.")
            print(f"Pt1: {pts[1]}, Pt2: {pts[2]}, Pt3: {pts[3]}, Water: {water_pt}")
            return

        delay = self.purchase_speed_var.get()

        # 1. Open Menu
        self.press_key('e', duration=0.1)
        time.sleep(delay)
        
        # 2. Click Pt 1
        self.click_at(pts[1])
        time.sleep(delay)
        
        # 3. Click Pt 2
        self.click_at(pts[2])
        time.sleep(delay)
        
        # 4. Type Amount
        self.type_text(self.amount_var.get())
        time.sleep(delay)
        
        # 5. Click Pt 1
        self.click_at(pts[1])
        time.sleep(delay)
        
        # 6. Click Pt 3
        self.click_at(pts[3])
        time.sleep(delay)
        
        # 7. Click Pt 2
        self.click_at(pts[2])
        time.sleep(delay)
        
        # 8. Move to Water Point (Universal)
        self.move_and_wiggle(water_pt)
        time.sleep(delay)

        self.needs_bait_reselect = True

        # --- MODIFICATION: RESET ROD STATE ---
        # Add another rod key press to "toggle out" the rod before final equip
        rod_key = self.rod_key_var.get()
        self.press_key(rod_key, 0.1)
        time.sleep(0.3) 
        # --------------------------------------

        self.force_equip_rod()

    def run_auto_craft(self):
        print("Starting Auto Craft...")
        if not self.craft_coords['craft_btn']: return
        click_delay = self.craft_speed_var.get()
        menu_delay = self.craft_menu_delay_var.get()
        try:
            craft_orders = [
                ('legendary', self.legendary_count.get()),
                ('rare', self.rare_count.get()),
                ('common', self.common_count.get())
            ]
            self.press_key('e', duration=0.1)
            time.sleep(menu_delay)
            for type_name, count in craft_orders:
                if count <= 0: continue
                pos = self.craft_coords[type_name]
                if not pos: continue
                self.click_at(pos)
                time.sleep(click_delay)
                btn_pos = self.craft_coords['craft_btn']
                for i in range(count):
                    self.click_at(btn_pos)
                    time.sleep(click_delay)
                time.sleep(click_delay)
            self.press_key('e', duration=0.1)
            time.sleep(0.2)
            self.needs_bait_reselect = True
            self.force_equip_rod()
        except: pass

    def store_fruit(self):
        print(f"Stored Fruit.")
        try:
            fruit_key = self.fruit_key_var.get()
            not_rod = self.non_rod_key_var.get()
            delay = self.fruit_speed_var.get()
            
            # Switch Logic inside Store Fruit
            if not self.always_rod_var.get():
                keyboard.press_and_release(not_rod)
                time.sleep(delay)
                
            keyboard.press_and_release(fruit_key)
            time.sleep(delay)
            if self.fruit_coords['fruit_slot']:
                self.click_at(self.fruit_coords['fruit_slot'])
                time.sleep(delay)
            time.sleep(delay)
            keyboard.press_and_release('backspace')
            time.sleep(delay)
            self.force_equip_rod()
            self.needs_bait_reselect = True
        except: pass

    def select_bait(self):
        if self.fruit_coords['bait_slot']:
            self.click_at(self.fruit_coords['bait_slot'])
            time.sleep(0.5)

    # ================= Main Worker Loop =================

    def toggle_main_loop(self):
        self.main_loop_active = not self.main_loop_active
        if self.main_loop_active:
            # Check for coordinates before starting
            if self.auto_purchase_var.get():
                if not all([self.point_coords[1], self.point_coords[2], self.point_coords[3], self.craft_coords['water']]):
                    messagebox.showwarning("Setup", "Set Pts 1-3 AND Water Pt for Auto Buy!")
                    self.main_loop_active = False
                    return
            
            if self.auto_craft_var.get() and not self.craft_coords['craft_btn']:
                messagebox.showwarning("Setup", "Set Main Craft Button!")
                self.main_loop_active = False
                return
            
            self.needs_bait_reselect = True
            self.status_indicator.config(text="RUNNING", bg=self.colors['success'])
            threading.Thread(target=self.worker, daemon=True).start()
        else:
            self.status_indicator.config(text="STOPPED", bg=self.colors['danger'])
            if self.is_clicking:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0,0,0,0)
                self.is_clicking = False

    def perform_post_fish_tasks(self):
        """Runs the checklist of tasks (Fruit/Buy/Craft)"""
        self.fish_catch_counter += 1
        
        # 1. Fruit Storage
        if self.fruit_storage_var.get():
            if self.fish_catch_counter % self.fruit_check_loop_var.get() == 0:
                self.store_fruit()
        
        # 2. Auto Buy
        if self.auto_purchase_var.get():
            self.purchase_counter += 1
            if self.purchase_counter >= self.loops_var.get():
                self.run_auto_purchase()
                self.purchase_counter = 0

        # 3. Auto Craft
        if self.auto_craft_var.get():
            self.craft_counter += 1
            if self.craft_counter >= self.craft_loop_var.get():
                self.run_auto_craft()
                self.craft_counter = 0

    def worker(self):
        sct = mss.mss()
        time.sleep(1.0)
        
        # --- RUN ON START CHECK ---
        # Run Auto Purchase immediately if enabled, INDEPENDENT of other toggles
        if self.auto_purchase_var.get():
            print("Performing initial purchase on start...")
            self.run_auto_purchase()
            self.purchase_counter = 0

        # Initial Cast
        self.cast_line()
        time.sleep(self.rod_reset_var.get())

        last_detection_time = time.time()
        was_detecting = False
        
        while self.main_loop_active:
            try:
                # 1. Capture Screen
                monitor = {
                    'left': self.overlay_area['x'], 'top': self.overlay_area['y'],
                    'width': self.overlay_area['width'], 'height': self.overlay_area['height']
                }
                img = np.array(sct.grab(monitor))

                # 2. Find Blue Bar (Target Container)
                blue_mask = (
                    (img[:,:,2] == COLOR_TARGET_BLUE[2]) & # R
                    (img[:,:,1] == COLOR_TARGET_BLUE[1]) & # G
                    (img[:,:,0] == COLOR_TARGET_BLUE[0])   # B
                )
                
                cols = np.where(np.any(blue_mask, axis=0))[0]
                
                if cols.size == 0:
                    # --- DETECTION LOST (Finished Fishing or Timeout) ---
                    current_time = time.time()
                    
                    if was_detecting:
                        # Just finished a cycle
                        print("Bar gone. Cycle complete.")
                        self.perform_post_fish_tasks()
                        
                        self.cast_line()
                        time.sleep(self.rod_reset_var.get())
                        
                        was_detecting = False
                        last_detection_time = time.time()
                    
                    elif (current_time - last_detection_time) > self.timeout_var.get():
                        # Timeout
                        print("Timeout. Resetting...")
                        self.perform_post_fish_tasks() # Safety check
                        self.cast_line()
                        time.sleep(self.rod_reset_var.get())
                        last_detection_time = time.time()

                    time.sleep(0.1)
                    continue

                # 3. Find "Real Area" Height (Dark pixels)
                min_x, max_x = cols[0], cols[-1]
                crop_width = max_x - min_x
                
                # Check within the column range for Dark pixels to find Top/Bottom
                center_x_rel = crop_width // 2
                real_col = img[:, min_x + center_x_rel, :]
                
                dark_mask_y = (
                    (real_col[:, 2] == COLOR_DARK[2]) &
                    (real_col[:, 1] == COLOR_DARK[1]) &
                    (real_col[:, 0] == COLOR_DARK[0])
                )
                rows = np.where(dark_mask_y)[0]
                
                if rows.size == 0: continue
                
                min_y, max_y = rows[0], rows[-1]
                real_height = max_y - min_y
                if real_height <= 0: continue

                # 4. Crop to Real Game Area
                game_area = img[min_y:max_y+1, min_x:max_x+1]
                
                # 5. Find White Indicator (Top Y)
                white_mask = (
                    (game_area[:,:,2] == COLOR_WHITE[2]) &
                    (game_area[:,:,1] == COLOR_WHITE[1]) &
                    (game_area[:,:,0] == COLOR_WHITE[0])
                )
                white_rows = np.where(np.any(white_mask, axis=1))[0]
                
                if white_rows.size == 0: continue
                
                white_top_y = white_rows[0]
                white_height = white_rows[-1] - white_rows[0]
                
                was_detecting = True
                last_detection_time = time.time()

                # 6. Find Dark Target Zones
                check_col = game_area[:, crop_width // 2]
                
                is_dark = (
                    (check_col[:, 2] == COLOR_DARK[2]) &
                    (check_col[:, 1] == COLOR_DARK[1]) &
                    (check_col[:, 0] == COLOR_DARK[0])
                )
                
                # Find continuous sections allowing for gaps
                max_gap = max(3, white_height * 2)
                
                dark_sections = []
                current_start = None
                gap = 0
                
                for r in range(len(is_dark)):
                    if is_dark[r]:
                        if current_start is None: current_start = r
                        gap = 0
                    else:
                        if current_start is not None:
                            gap += 1
                            if gap > max_gap:
                                dark_sections.append((current_start, r - gap))
                                current_start = None
                                gap = 0
                
                if current_start is not None:
                    dark_sections.append((current_start, len(is_dark) - 1))
                
                if not dark_sections: continue
                
                # Pick largest section (The Target)
                largest = max(dark_sections, key=lambda s: s[1] - s[0])
                target_middle_y = (largest[0] + largest[1]) // 2

                # 7. PD Controller
                raw_error = target_middle_y - white_top_y
                normalized_error = raw_error / real_height
                
                derivative = normalized_error - self.previous_error
                self.previous_error = normalized_error
                
                kp = self.kp_var.get()
                kd = self.kd_var.get()
                
                output = (kp * normalized_error) + (kd * derivative)

                if output > 0:
                    if not self.is_clicking:
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0,0,0,0)
                        self.is_clicking = True
                else:
                    if self.is_clicking:
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0,0,0,0)
                        self.is_clicking = False
                
                time.sleep(0.01)

            except Exception as e:
                print(f"Loop Error: {e}")
                time.sleep(1)

    def exit_app(self):
        self.main_loop_active = False
        if self.overlay_window: self.overlay_window.destroy()
        try: keyboard.unhook_all()
        except: pass
        self.root.destroy()
        sys.exit(0)

if __name__ == '__main__':
    root = tk.Tk()
    app = ModernGPOBot(root)
    root.mainloop()