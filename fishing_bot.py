import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import sys
import ctypes
import math

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
# Color Detection (RGB)
# The static blue bar color in the minigame
COLOR_BAR_CONTAINER = (85, 170, 255)
# The dark background color of the "Safe Zone"
COLOR_SAFE_ZONE_BACKGROUND = (25, 25, 25)
# The moving white indicator color
COLOR_MOVING_INDICATOR = (255, 255, 255)

# Tolerance for color matching
COLOR_TOLERANCE = 25

class ModernGPOBot:
    def __init__(self, root):
        self.root = root
        self.root.title('GPO FISHING MACRO')
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
        self.purchase_counter = 0
       
        self.dpi_scale = self.get_dpi_scale()
       
        # Overlay Geometry
        base_width = 250
        base_height = 500
        self.overlay_area = {
            'x': int(100 * self.dpi_scale),
            'y': int(100 * self.dpi_scale),
            'width': int(base_width * self.dpi_scale),
            'height': int(base_height * self.dpi_scale)
        }
       
        self.previous_error = 0
        self.point_coords = {1: None, 2: None, 3: None, 4: None}
        self.hotkeys = {'toggle_loop': 'f1', 'toggle_overlay': 'f2', 'exit': 'f3'}

        self.setup_styles()
        self.setup_ui()
        self.register_hotkeys()
        self.root.update_idletasks()
        self.root.minsize(400, 700)

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
        main_container = ttk.Frame(self.root, padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill='x', pady=(0, 15))
        ttk.Label(header_frame, text='INK_GPO FISH MACRO', style='Header.TLabel').pack(side='left')
        self.status_indicator = tk.Label(header_frame, text="STOPPED", bg=self.colors['danger'], fg='white', font=('Segoe UI', 8, 'bold'), padx=8, pady=2)
        self.status_indicator.pack(side='right')

        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill='x', pady=(0, 10))
        self.overlay_label = ttk.Label(status_frame, text='Overlay: HIDDEN', foreground='#666666')
        self.overlay_label.pack(side='right')

        self.create_card(main_container, "Auto Purchase", self.setup_auto_buy_content)
        self.create_card(main_container, "Mechanics & Timing", self.setup_mechanics_content)
        self.create_card(main_container, "Hotkeys", self.setup_hotkeys_content)

        self.msg_label = ttk.Label(main_container, text="Ready.", foreground=self.colors['accent'])
        self.msg_label.pack(side='bottom', fill='x', pady=10)

    def create_card(self, parent, title, content_func):
        card = ttk.Frame(parent, style='Card.TFrame', padding=10)
        card.pack(fill='x', pady=5)
        ttk.Label(card, text=title, style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))
        content_func(card)

    def setup_auto_buy_content(self, parent):
        self.auto_purchase_var = tk.BooleanVar(value=True)
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
       
        ttk.Label(grid, text="Interact Delay (s):", style='Card.TLabel').grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.interact_delay_var = tk.DoubleVar(value=2.0)
        tk.Spinbox(grid, from_=0.1, to=10.0, increment=0.1, textvariable=self.interact_delay_var, width=8, bg=self.colors['bg'], fg='white', relief='flat').grid(row=1, column=1, pady=2)

        btn_grid = ttk.Frame(parent, style='Card.TFrame')
        btn_grid.pack(fill='x', pady=5)
        self.point_buttons = {}
        for i in range(1, 5):
            r, c = divmod(i-1, 2)
            btn = ttk.Button(btn_grid, text=f"Set Pt {i}", command=lambda x=i: self.capture_mouse_click(x))
            btn.grid(row=r, column=c, sticky='ew', padx=2, pady=2)
            btn_grid.columnconfigure(c, weight=1)
            self.point_buttons[i] = btn

    def setup_mechanics_content(self, parent):
        grid = ttk.Frame(parent, style='Card.TFrame')
        grid.pack(fill='x')
        ttk.Label(grid, text="Kp (Strength):", style='Card.TLabel').grid(row=0, column=0, sticky='w', padx=5)
        self.kp_var = tk.DoubleVar(value=0.1)
        tk.Scale(grid, from_=0.0, to=2.0, resolution=0.01, variable=self.kp_var, orient='horizontal', bg=self.colors['panel'], fg='white', highlightthickness=0, length=100).grid(row=0, column=1)
        ttk.Label(grid, text="Kd (Stability):", style='Card.TLabel').grid(row=1, column=0, sticky='w', padx=5)
        self.kd_var = tk.DoubleVar(value=0.5)
        tk.Scale(grid, from_=0.0, to=2.0, resolution=0.01, variable=self.kd_var, orient='horizontal', bg=self.colors['panel'], fg='white', highlightthickness=0, length=100).grid(row=1, column=1)
       
        ttk.Label(grid, text="Rod Reset (s):", style='Card.TLabel').grid(row=0, column=2, sticky='w', padx=15)
        self.rod_reset_var = tk.DoubleVar(value=3.0)
        tk.Spinbox(grid, from_=0.0, to=10.0, increment=0.1, textvariable=self.rod_reset_var, width=6, bg=self.colors['bg'], fg='white', relief='flat').grid(row=0, column=3)
        ttk.Label(grid, text="Timeout (s):", style='Card.TLabel').grid(row=1, column=2, sticky='w', padx=15)
        self.timeout_var = tk.DoubleVar(value=15.0)
        tk.Spinbox(grid, from_=1.0, to=120.0, increment=1.0, textvariable=self.timeout_var, width=6, bg=self.colors['bg'], fg='white', relief='flat').grid(row=1, column=3)

    def setup_hotkeys_content(self, parent):
        for i, (key_id, label_text) in enumerate([('toggle_loop', 'Start/Stop'), ('toggle_overlay', 'Overlay'), ('exit', 'Exit App')]):
            f = ttk.Frame(parent, style='Card.TFrame')
            f.pack(fill='x', pady=1)
            ttk.Label(f, text=label_text, style='Card.TLabel', width=15).pack(side='left')
            lbl = tk.Label(f, text=self.hotkeys[key_id].upper(), bg=self.colors['bg'], fg='white', width=10, relief='flat')
            lbl.pack(side='left', padx=10)
            ttk.Button(f, text="Bind", width=6, command=lambda k=key_id, l=lbl: self.start_rebind(k, l)).pack(side='right')

    # ================= Click & Input Logic =================

    def capture_mouse_click(self, idx):
        self.msg_label.config(text=f"Click anywhere to set Point {idx}...", foreground=self.colors['accent'])
        def on_click(x, y, button, pressed):
            if pressed:
                self.point_coords[idx] = (x, y)
                self.root.after(0, lambda: self.finish_capture(idx))
                return False
        pynput_mouse.Listener(on_click=on_click).start()

    def finish_capture(self, idx):
        self.point_buttons[idx].config(text=f"Pt {idx} Set", style='Accent.TButton')
        self.msg_label.config(text=f"Point {idx} set.", foreground=self.colors['success'])

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
            # Wiggle
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 1, 1, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -1, -1, 0, 0)
            time.sleep(0.02)
            # Click
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except: pass

    def move_and_wiggle(self, coords):
        """Moves to coords and does the small wiggle, but DOES NOT click."""
        if not coords: return
        try:
            x, y = int(coords[0]), int(coords[1])
            win32api.SetCursorPos((x, y))
            time.sleep(0.05)
            # The "small movement" (Wiggle)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 1, 1, 0, 0)
            time.sleep(0.02)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -1, -1, 0, 0)
        except: pass

    def _move_to(self, coords):
        """Moves mouse to coords WITHOUT clicking and WITHOUT wiggle"""
        if not coords: return
        try:
            x, y = int(coords[0]), int(coords[1])
            win32api.SetCursorPos((x, y))
            time.sleep(0.05)
        except: pass

    def press_key(self, k, duration=0.3):
        vk = win32api.VkKeyScan(k)
        scan = win32api.MapVirtualKey(vk & 0xFF, 0)
        win32api.keybd_event(vk, scan, 0, 0)
        time.sleep(duration)
        win32api.keybd_event(vk, scan, win32con.KEYEVENTF_KEYUP, 0)

    def type_text(self, text):
        for char in str(text):
            self.press_key(char, 0.02)
            time.sleep(0.02)

    def cast_line(self):
        print("Casting...")
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(1.0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.is_clicking = False
        print("Cast Complete.")

    def run_auto_purchase(self):
        print("Starting Auto Purchase...")
        pts = self.point_coords
        if not all([pts[1], pts[2], pts[3], pts[4]]):
            print("Points not set!")
            return
        try:
            print("Pressing E...")
            self.press_key('e', duration=0.5)
            time.sleep(self.interact_delay_var.get())
           
            # Sequence: 1 -> 2 -> 1 -> 3 -> 2 -> 4 (Move + Wiggle)
            self.click_at(pts[1])
            time.sleep(0.5)
            self.click_at(pts[2])
            time.sleep(0.5)
            self.type_text(self.amount_var.get())
            time.sleep(0.5)
            self.click_at(pts[1])
            time.sleep(0.5)
            self.click_at(pts[3])
            time.sleep(0.5)
            self.click_at(pts[2])
            time.sleep(0.5)
           
            # Point 4: Move + Wiggle (No Click)
            self.move_and_wiggle(pts[4])
            time.sleep(1.0)
           
        except Exception as e:
            print(f"Purchase Error: {e}")

    # ================= Main Worker Loop =================

    def toggle_main_loop(self):
        self.main_loop_active = not self.main_loop_active
        if self.main_loop_active:
            if self.auto_purchase_var.get():
                if not all(self.point_coords.values()):
                    messagebox.showwarning("Setup", "Please set all 4 points first.")
                    self.main_loop_active = False
                    return
            self.status_indicator.config(text="RUNNING", bg=self.colors['success'])
            threading.Thread(target=self.worker, daemon=True).start()
        else:
            self.status_indicator.config(text="STOPPED", bg=self.colors['danger'])

    def worker(self):
        sct = mss.mss()
        time.sleep(1.0) # Safety delay
       
        if self.auto_purchase_var.get():
            self.run_auto_purchase()

        self.cast_line()
        time.sleep(self.rod_reset_var.get())

        last_detection_time = time.time()
        was_detecting = False
       
        # Track where the white bar was last seen for recovery logic
        last_known_white_y = 0
        white_bar_lost_time = 0

        while self.main_loop_active:
            try:
                monitor = {
                    'left': self.overlay_area['x'], 'top': self.overlay_area['y'],
                    'width': self.overlay_area['width'], 'height': self.overlay_area['height']
                }
               
                img = np.array(sct.grab(monitor))

                # 1. Find Blue Bar (Container)
                blue_mask = (
                    (np.abs(img[:,:,2] - COLOR_BAR_CONTAINER[0]) < COLOR_TOLERANCE) &
                    (np.abs(img[:,:,1] - COLOR_BAR_CONTAINER[1]) < COLOR_TOLERANCE) &
                    (np.abs(img[:,:,0] - COLOR_BAR_CONTAINER[2]) < COLOR_TOLERANCE)
                )

                col_counts = np.sum(blue_mask, axis=0)
                valid_cols = np.where(col_counts > 100)[0]

                if valid_cols.size == 0:
                    # --- No Blue Bar Found ---
                    if was_detecting and (time.time() - last_detection_time > 1.0):
                        print("Bar lost completely. Cycle finished/Resetting.")
                        was_detecting = False
                       
                        # Handle Auto Buy / Re-cast logic here
                        if self.auto_purchase_var.get():
                            self.purchase_counter += 1
                            if self.purchase_counter >= self.loops_var.get():
                                self.run_auto_purchase()
                                self.purchase_counter = 0
                       
                        self.cast_line()
                        time.sleep(self.rod_reset_var.get())
                        last_detection_time = time.time()
                   
                    # Timeout Logic
                    if time.time() - last_detection_time > self.timeout_var.get():
                        print("Timeout. Recasting.")
                        self.cast_line()
                        time.sleep(self.rod_reset_var.get())
                        last_detection_time = time.time()
                   
                    time.sleep(0.1)
                    continue

                # 2. Crop to the "Smart Bar" Area
                min_x, max_x = valid_cols[0], valid_cols[-1]
                col_slice = blue_mask[:, min_x:max_x]
                row_counts = np.sum(col_slice, axis=1)
                valid_rows = np.where(row_counts > 5)[0]
               
                if valid_rows.size == 0: continue
               
                min_y, max_y = valid_rows[0], valid_rows[-1]
                bar_height = max_y - min_y
               
                crop = img[min_y:max_y, min_x:max_x, :]
               
                was_detecting = True
                last_detection_time = time.time()

                # 3. Find Dark Zone (Target)
                dark_mask = (
                    (np.abs(crop[:,:,2] - COLOR_SAFE_ZONE_BACKGROUND[0]) < 10) &
                    (np.abs(crop[:,:,1] - COLOR_SAFE_ZONE_BACKGROUND[1]) < 10) &
                    (np.abs(crop[:,:,0] - COLOR_SAFE_ZONE_BACKGROUND[2]) < 10)
                )
                dark_indices = np.where(np.any(dark_mask, axis=1))[0]
               
                # Default target to center if not found (failsafe)
                target_y = bar_height / 2
                if dark_indices.size > 0:
                    diffs_d = np.diff(dark_indices)
                    splits_d = np.where(diffs_d > 5)[0] + 1
                    sections_d = np.split(dark_indices, splits_d)
                    longest_d = max(sections_d, key=len)
                    if len(longest_d) > 0:
                        target_y = (longest_d[0] + longest_d[-1]) // 2

                # 4. Find White Indicator (WITH STUCK RECOVERY)
                white_mask = (
                    (np.abs(crop[:,:,2] - COLOR_MOVING_INDICATOR[0]) < 10) &
                    (np.abs(crop[:,:,1] - COLOR_MOVING_INDICATOR[1]) < 10) &
                    (np.abs(crop[:,:,0] - COLOR_MOVING_INDICATOR[2]) < 10)
                )
                white_coords = np.argwhere(white_mask)

                indicator_y = 0

                if white_coords.size == 0:
                    # === RECOVERY LOGIC (0.1s Delay) ===
                    current_time = time.time()
                   
                    if white_bar_lost_time == 0:
                        white_bar_lost_time = current_time
                   
                    # If lost for > 0.2 seconds, it's likely stuck at an edge
                    if current_time - white_bar_lost_time > 0.2:
                        print("Stuck! Attempting recovery clicks...")
                       
                        # If last seen near the BOTTOM (High Y), we need to CLICK to raise it
                        if last_known_white_y > (bar_height / 2):
                            # Double tap to wiggle it up
                            for _ in range(2):
                                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0,0,0,0)
                                time.sleep(0.1) # UPDATED DELAY
                                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0,0,0,0)
                                time.sleep(0.1) # UPDATED DELAY
                        else:
                            # If last seen near the TOP (Low Y), we must RELEASE to drop it
                            if self.is_clicking:
                                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0,0,0,0)
                                self.is_clicking = False
                       
                        # IMPORTANT: Do NOT reset 'was_detecting' or 'continue' here.
                        # We want to allow the loop to continue scanning immediately.
                        continue

                else:
                    # Normal Operation: Found the white bar
                    white_bar_lost_time = 0
                    indicator_y = white_coords[:, 0].min()
                    last_known_white_y = indicator_y

                # 5. PID Control
                if bar_height == 0: continue
               
                error = target_y - indicator_y
                norm_error = error / bar_height
               
                derivative = norm_error - self.previous_error
                self.previous_error = norm_error
               
                output = (self.kp_var.get() * norm_error) + (self.kd_var.get() * derivative)

                if output > 0 and not self.is_clicking:
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0,0,0,0)
                    self.is_clicking = True
                elif output <= 0 and self.is_clicking:
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0,0,0,0)
                    self.is_clicking = False
                time.sleep(0.01)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

        if self.is_clicking:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0,0,0,0)
            self.is_clicking = False

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