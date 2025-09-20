#!/usr/bin/env python3
# obliterator_gui.py - (Version 3.2 - Guaranteed Splash Screen)
# GUI for the Obliterator Secure Wipe Tool

import tkinter
import customtkinter
import subprocess
import json
import datetime
import os
import threading
import base64

# --- Imports for the 'cryptography' library ---
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# --- Configuration ---
APP_NAME = "Obliterator"
APP_VERSION = "3.2-final"
THEME_COLOR = "dark-blue"
PRIVATE_KEY_PATH = "/mnt/home/obliterator/keys/private_key.pem"
CERT_DIR = "/mnt/home/obliterator/certificates/"
WIPE_SCRIPT_PATH = "/mnt/home/obliterator/wipe_disk.sh"

# --- [NEW] Splash Screen with Logo ---
class SplashScreen(customtkinter.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Obliterator")
        self.geometry("400x250")
        self.overrideredirect(True)

        # Center the splash screen
        parent.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        self.geometry(f"+{parent_x + parent_width // 2 - 200}+{parent_y + parent_height // 2 - 125}")

        # Simple shield logo
        logo_label = customtkinter.CTkLabel(self, text="🛡️", font=("Roboto", 60))
        logo_label.pack(pady=(30, 0))

        main_label = customtkinter.CTkLabel(self, text=APP_NAME, font=("Roboto", 40, "bold"))
        main_label.pack(pady=10)
        
        status_label = customtkinter.CTkLabel(self, text="Initializing Secure Environment...", font=("Roboto", 12))
        status_label.pack(pady=10)

        self.lift()

# --- Confirmation Dialog ---
class ConfirmationDialog(customtkinter.CTkToplevel):
    def __init__(self, parent, device_info):
        super().__init__(parent)
        self.transient(parent)
        self.title("CONFIRM DESTRUCTION")
        self.geometry("500x350")
        
        self.result = False
        self.device_info = device_info
        self.confirmation_token = "OBLITERATE"

        main_label = customtkinter.CTkLabel(self, text="WARNING: IRREVERSIBLE ACTION", font=("Roboto", 20, "bold"), text_color="red")
        main_label.pack(pady=10)
        
        info_text = f"You are about to permanently destroy all data on:\n\n"
        for dev in self.device_info:
            model = dev.get('model') or 'N/A'
            size = dev.get('size') or 'N/A'
            info_text += f"- {dev['name']} ({model}, {size})\n"
        
        info_label = customtkinter.CTkLabel(self, text=info_text, wraplength=450, justify=tkinter.LEFT)
        info_label.pack(pady=10, padx=20)
        
        instruction_label = customtkinter.CTkLabel(self, text=f'Type "{self.confirmation_token}" below to proceed.')
        instruction_label.pack(pady=5)
        
        self.entry = customtkinter.CTkEntry(self, width=200)
        self.entry.pack(pady=5)
        
        self.confirm_button = customtkinter.CTkButton(self, text="Confirm and Wipe", command=self.on_confirm, state="disabled")
        self.confirm_button.pack(pady=10)
        
        cancel_button = customtkinter.CTkButton(self, text="Cancel", command=self.destroy)
        cancel_button.pack(pady=5)

        self.entry.bind("<KeyRelease>", self.check_token)
        self.after(50, self.grab_set)

    def check_token(self, event):
        if self.entry.get() == self.confirmation_token:
            self.confirm_button.configure(state="normal")
        else:
            self.confirm_button.configure(state="disabled")

    def on_confirm(self):
        self.result = True
        self.destroy()

# --- Main Application ---
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Hide main window

        # --- THIS IS THE NEW, CORRECT LOGIC ---
        # 1. Create the splash screen
        self.splash = SplashScreen(self)

        # 2. Schedule the main window setup to run after 3 seconds (3000ms)
        self.after(3000, self.setup_main_window)

    def setup_main_window(self):
        """This function builds the main UI and is called after the splash screen delay."""
        self.title(APP_NAME)
        self.geometry("800x600")
        customtkinter.set_appearance_mode("Dark")
        customtkinter.set_default_color_theme(THEME_COLOR)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.selected_devices = []

        self.header_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.header_label = customtkinter.CTkLabel(self.header_frame, text=APP_NAME, font=("Roboto", 24, "bold"))
        self.header_label.pack(pady=10)

        self.device_frame = customtkinter.CTkFrame(self)
        self.device_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.device_frame.grid_columnconfigure(0, weight=1)
        self.device_widgets = {}

        self.control_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.control_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.control_frame.grid_columnconfigure((0, 2), weight=1)

        self.refresh_button = customtkinter.CTkButton(self.control_frame, text="Refresh Devices", command=self.populate_devices)
        self.refresh_button.grid(row=0, column=0, padx=10, pady=10)
        
        self.wipe_button = customtkinter.CTkButton(self.control_frame, text="Wipe Selected Drive(s)", command=self.start_wipe_process, state="disabled", fg_color="red", hover_color="darkred")
        self.wipe_button.grid(row=0, column=2, padx=10, pady=10)
        
        self.progress_frame = customtkinter.CTkFrame(self)
        self.progress_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.progress_label = customtkinter.CTkLabel(self.progress_frame, text="Status: Idle")
        self.progress_label.pack(pady=5)
        self.progress_bar = customtkinter.CTkProgressBar(self.progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=5, padx=10, fill="x")
        self.log_textbox = customtkinter.CTkTextbox(self, height=150, state="disabled")
        self.log_textbox.grid(row=4, column=0, sticky="nsew", padx=10, pady=10)

        self.populate_devices()

        # 3. Destroy splash screen and show the main window
        self.splash.destroy()
        self.deiconify()

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def detect_devices(self):
        try:
            result = subprocess.run(
                ['lsblk', '-d', '--json', '-o', 'NAME,MODEL,SERIAL,SIZE,TYPE'],
                capture_output=True, text=True, check=True
            )
            data = json.loads(result.stdout)
            return [dev for dev in data.get("blockdevices", []) if dev.get("type") in ["disk", "nvme"]]
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            self.log(f"Error detecting devices: {e}")
            return []

    def populate_devices(self):
        for widget in self.device_frame.winfo_children():
            widget.destroy()

        self.device_widgets.clear()
        devices = self.detect_devices()

        if not devices:
            label = customtkinter.CTkLabel(self.device_frame, text="No storage devices found.")
            label.pack(pady=20)
            return

        header = f"{'Select':<8} {'Device':<12} {'Model':<30} {'Serial':<25} {'Size':<10}"
        header_label = customtkinter.CTkLabel(self.device_frame, text=header, font=("monospace", 12))
        header_label.pack(fill="x", padx=10)

        for dev in devices:
            dev_path = f"/dev/{dev.get('name', 'N/A')}"
            var = tkinter.BooleanVar()
            
            display_text = (
                f"{dev_path:<12} "
                f"{(dev.get('model') or 'N/A'):<30} "
                f"{(dev.get('serial') or 'N/A'):<25} "
                f"{(dev.get('size') or 'N/A'):<10}"
            )

            checkbox = customtkinter.CTkCheckBox(
                self.device_frame, text=display_text, variable=var,
                font=("monospace", 12), command=self.update_selection_status
            )
            checkbox.pack(anchor="w", padx=10)
            self.device_widgets[dev_path] = {"var": var, "data": dev}
        self.update_selection_status()

    def update_selection_status(self):
        self.selected_devices = [
            info["data"] for path, info in self.device_widgets.items() if info["var"].get()
        ]
        self.wipe_button.configure(state="normal" if self.selected_devices else "disabled")

    def start_wipe_process(self):
        dialog = ConfirmationDialog(self, self.selected_devices)
        self.wait_window(dialog)
        
        if dialog.result:
            self.log(f"Confirmation received. Starting wipe for {len(self.selected_devices)} device(s).")
            self.wipe_button.configure(state="disabled")
            self.refresh_button.configure(state="disabled")
            
            device_to_wipe = self.selected_devices[0]
            threading.Thread(target=self.run_wipe_script, args=(device_to_wipe,), daemon=True).start()

    def run_wipe_script(self, device_data):
        device_path = f"/dev/{device_data['name']}"
        command = ['bash', WIPE_SCRIPT_PATH, device_path, 'OBLITERATE']
        
        self.log(f"Executing command: {' '.join(command)}")
        
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            
            for line in iter(process.stdout.readline, ''):
                self.after(0, self.handle_script_output, line.strip())

            process.wait()
            
            if process.returncode == 0:
                self.after(0, self.finish_wipe, device_data, True)
            else:
                stderr_output = process.stderr.read()
                self.after(0, self.log, f"ERROR wiping {device_path}. Script failed with output:\n{stderr_output}")
                self.after(0, self.finish_wipe, device_data, False)

        except Exception as e:
            self.after(0, self.log, f"CRITICAL FAILURE: Could not start wipe process: {e}")
            self.after(0, self.finish_wipe, device_data, False)
            
    def handle_script_output(self, line):
        self.log(line)
        if line.startswith("PROGRESS:"):
            try:
                parts = line.split(':')
                progress_part = parts[1]
                status_message = parts[2]
                current_pass, total_passes = map(int, progress_part.split('/'))
                progress_value = float(current_pass) / float(total_passes)
                self.progress_bar.set(progress_value)
                self.progress_label.configure(text=f"Status: Pass {current_pass} of {total_passes} - {status_message}")
            except (IndexError, ValueError):
                self.progress_label.configure(text="Status: Processing...")
        elif "STATUS:SUCCESS" in line:
            self.progress_bar.set(1)
            self.progress_label.configure(text="Status: Wipe Complete!")

    def finish_wipe(self, device_data, success):
        if success:
            self.log(f"Successfully wiped {device_data['name']}. Generating certificate...")
            self.generate_certificate(device_data)
        else:
            self.log(f"Failed to wipe {device_data['name']}.")
        
        self.progress_label.configure(text="Status: Idle")
        self.progress_bar.set(0)
        self.wipe_button.configure(state="normal")
        self.refresh_button.configure(state="normal")
        self.populate_devices()

    def generate_certificate(self, device_data):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        serial = device_data.get('serial') or 'UNKNOWN_SERIAL'
        
        cert = {
            "iss": APP_NAME, "ver": APP_VERSION, "iat": timestamp,
            "media": {
                "type": device_data.get("type"), "model": device_data.get("model"),
                "serial": serial, "size": device_data.get("size")
            },
            "sanitization": {
                "method": "Clear", "technique": "5-Pass Overwrite", "status": "Success"
            },
            "verification": {
                "method": "Post-Wipe Sampling Check", "status": "Success"
            }
        }
        
        try:
            with open(PRIVATE_KEY_PATH, 'rb') as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None)
            
            json_payload_bytes = json.dumps(cert, sort_keys=True).encode('utf-8')

            signature = private_key.sign(
                json_payload_bytes, padding.PKCS1v15(), hashes.SHA256()
            )
            
            signed_cert_container = {
                "payload": cert,
                "signature": base64.b64encode(signature).decode('utf-8')
            }
            
            filename = f"wipe-{datetime.datetime.now():%Y%m%d-%H%M%S}-{serial}.json"
            filepath = os.path.join(CERT_DIR, filename)
            
            if not os.path.exists(CERT_DIR):
                os.makedirs(CERT_DIR)
                
            with open(filepath, 'w') as f:
                json.dump(signed_cert_container, f, indent=4)
                
            self.log(f"Certificate saved to {filepath}")
            
        except Exception as e:
            self.log(f"ERROR: Could not sign or save certificate: {e}")


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: This application requires root privileges to access block devices.")
        print("Please run with 'sudo python3 obliterator_gui.py'")
    else:
        app = App()
        app.mainloop()
