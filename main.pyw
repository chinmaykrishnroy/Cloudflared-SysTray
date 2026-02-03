"""
Cloudflare Tunnel Manager (Tray Application)
--------------------------------------------
A lightweight system tray utility to manage a Cloudflare Tunnel process.
Features:
- Silent background execution (no terminal window).
- Visual status indicators (Red/Green/Blinking).
- Log monitoring for connection verification.
- Singleton instance enforcement.
- FORCE-REFRESH Menus (Fixes stuck buttons).

Dependencies: pystray, Pillow
"""

import subprocess
import pystray
from PIL import Image, ImageDraw
import threading
import os
import sys
import time
import socket

# =============================================================================
# CONFIGURATION
# =============================================================================

TUNNEL_COMMAND = ["cloudflared", "tunnel", "run", "prefect-home"]
LOG_FILE = "tunnel.log"
APP_NAME = "TunnelTray"
SINGLE_INSTANCE_PORT = 26492 
AUTO_START_TUNNEL = True 

# =============================================================================
# VISUAL ASSETS (COLORS)
# =============================================================================

COLOR_GREEN    = "#00aa00"  # Status: Connected
COLOR_RED      = "#aa0000"  # Status: Stopped
COLOR_YELLOW   = "#aaaa00"  # Status: Connecting (Blinking)
COLOR_ORANGE   = "#aa5500"  # Status: Stopping (Blinking)
COLOR_BLANK    = "#333333"  # Status: Off-cycle blink color

# =============================================================================
# GLOBAL STATE
# =============================================================================

process = None
current_state = "CONNECTING" if AUTO_START_TUNNEL else "STOPPED"
instance_socket = None 

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def enforce_single_instance():
    global instance_socket
    instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        instance_socket.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
    except socket.error as e:
        print(f"(!) DEBUG: Bind failed because: {e}")
        return False
    return True

def create_image(color):
    width, height = 64, 64
    image = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, height), fill=color)
    return image

# =============================================================================
# MENU BUILDER (THE FIX)
# =============================================================================

def update_menu(icon):
    """
    Replaces the icon's menu with a fresh one based on current_state.
    This fixes the 'stuck button' bug by forcing a UI refresh.
    """
    # Define items based on exact state
    if current_state == "STOPPED":
        # Show START, Hide STOP
        menu_items = [
            pystray.MenuItem("Start Tunnel", start_tunnel),
            pystray.MenuItem("Stop Tunnel", stop_tunnel, visible=False)
        ]
    elif current_state == "RUNNING":
        # Show STOP, Hide START
        menu_items = [
            pystray.MenuItem("Start Tunnel", start_tunnel, visible=False),
            pystray.MenuItem("Stop Tunnel", stop_tunnel)
        ]
    elif current_state == "CONNECTING":
        # Show Disabled "Connecting..."
        menu_items = [
            pystray.MenuItem("Connecting...", lambda i,j: None, enabled=False)
        ]
    elif current_state == "STOPPING":
        # Show Disabled "Stopping..."
        menu_items = [
            pystray.MenuItem("Stopping...", lambda i,j: None, enabled=False)
        ]
    else:
        menu_items = []

    # Add common items
    menu_items.extend([
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("View Logs", open_logs),
        pystray.MenuItem("Quit", quit_app)
    ])

    # Assign the new menu to the icon immediately
    icon.menu = pystray.Menu(*menu_items)

# =============================================================================
# ANIMATION & MONITORING THREADS
# =============================================================================

def icon_animator(icon):
    toggle = False
    while icon._running:
        if current_state == "CONNECTING":
            color = COLOR_YELLOW if toggle else COLOR_BLANK
            icon.icon = create_image(color)
            toggle = not toggle
            time.sleep(0.5)
            
        elif current_state == "STOPPING":
            color = COLOR_ORANGE if toggle else COLOR_BLANK
            icon.icon = create_image(color)
            toggle = not toggle
            time.sleep(0.2)
            
        elif current_state == "RUNNING":
            if icon.icon.getpixel((0,0)) != (0, 170, 0): 
                icon.icon = create_image(COLOR_GREEN)
            time.sleep(0.5)
            
        elif current_state == "STOPPED":
            if icon.icon.getpixel((0,0)) != (170, 0, 0): 
                icon.icon = create_image(COLOR_RED)
            time.sleep(0.5)
        else:
            time.sleep(0.5)

def monitor_connection(icon):
    global current_state
    try:
        if not os.path.exists(LOG_FILE):
            time.sleep(1)

        with open(LOG_FILE, "r") as f:
            f.seek(0, 2) 
            while current_state == "CONNECTING":
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    if process and process.poll() is not None:
                        current_state = "STOPPED"
                        update_menu(icon) # <--- Update Menu on Crash
                        break
                    continue
                
                if "Registered tunnel connection" in line:
                    current_state = "RUNNING"
                    update_menu(icon) # <--- Update Menu on Success
                    icon.notify("Tunnel Connected Successfully!", APP_NAME)
                    break
    except Exception:
        time.sleep(3)
        if current_state == "CONNECTING" and process:
            current_state = "RUNNING"
            update_menu(icon)

def crash_watcher(icon):
    global current_state, process
    while icon._running:
        if current_state in ["RUNNING", "CONNECTING"] and process and process.poll() is not None:
            process = None
            current_state = "STOPPED"
            update_menu(icon) # <--- Update Menu on Crash
            icon.notify("Tunnel Crashed Unexpectedly", "Error")
        time.sleep(2)

# =============================================================================
# CONTROL FUNCTIONS
# =============================================================================

def start_tunnel(icon, item):
    global process, current_state
    
    if process and process.poll() is None:
        return 

    try:
        current_state = "CONNECTING"
        update_menu(icon) # <--- Update Menu Immediately
        
        with open(LOG_FILE, "a") as log:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                TUNNEL_COMMAND,
                stdout=log,
                stderr=log,
                creationflags=0x08000000, 
                text=True
            )
        
        threading.Thread(target=monitor_connection, args=(icon,), daemon=True).start()
        
    except Exception as e:
        current_state = "STOPPED"
        update_menu(icon)
        icon.notify(f"Failed to start: {e}", "Error")

def stop_tunnel(icon, item):
    global process, current_state
    
    if not process:
        current_state = "STOPPED"
        update_menu(icon)
        return

    current_state = "STOPPING"
    update_menu(icon)
    time.sleep(0.5) 

    try:
        process.kill()
        process.wait(timeout=3)
    except:
        pass
    finally:
        process = None
        current_state = "STOPPED"
        update_menu(icon) # <--- Update Menu on Stop
        icon.notify("Tunnel Stopped", APP_NAME)

def open_logs(icon, item):
    if os.path.exists(LOG_FILE):
        subprocess.run(["notepad.exe", LOG_FILE])
    else:
        icon.notify("No logs found yet.", "Info")

def quit_app(icon, item):
    stop_tunnel(icon, item)
    icon.stop()

def setup(icon):
    icon.visible = True
    
    # Initialize Menu State
    update_menu(icon)
    
    threading.Thread(target=icon_animator, args=(icon,), daemon=True).start()
    threading.Thread(target=crash_watcher, args=(icon,), daemon=True).start()
    
    if AUTO_START_TUNNEL:
        start_tunnel(icon, None)
    else:
        global current_state
        current_state = "STOPPED"
        update_menu(icon)

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    if not enforce_single_instance():
        print("(!) ERROR: App is already running!")
        print(f"(!) Port {SINGLE_INSTANCE_PORT} is occupied.")
        print("(!) Check your System Tray or Task Manager.")
        sys.exit(0)

    # Note: We pass None for menu initially; setup() will build it immediately.
    icon = pystray.Icon(APP_NAME, create_image(COLOR_RED), "Cloudflare Tunnel Manager", menu=None)
    icon.run(setup)