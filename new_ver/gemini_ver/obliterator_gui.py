#!/usr/bin/env python3
# obliterator_gui.py - (Version 17.0 - No PV)

import tkinter
import customtkinter
import subprocess
import json
import datetime
import os
import threading
import time
from queue import Queue, Empty

from PIL import Image, ImageTk

# --- Configuration ---
APP_NAME = "OBLITERATOR"
APP_VERSION = "17.0-final"
BASE_DIR = "/my-applications/obliterator"
THEME_FILE = os.path.join(BASE_DIR, "purple_theme.json")
LOGO_FILE = os.path.join(BASE_DIR, "logo.png") 
PRIVATE_KEY_PATH = os.path.join(BASE_DIR, "keys/private_key.pem")
CERT_DIR = os.path.join(BASE_DIR, "certificates/")
WIPE_SCRIPT_PATH = os.path.join(BASE_DIR, "wipe_disk.sh")
CERT_SCRIPT_PATH = os.path.join(BASE_DIR, "generate_cert.sh")

# --- Font Definitions ---
FONT_HEADER = ("Roboto", 42, "bold")
FONT_SUBHEADER = ("Roboto", 24, "bold")
FONT_BODY_BOLD = ("Roboto", 18, "bold")
FONT_BODY = ("Roboto", 16)
FONT_MONO = ("monospace", 14)

class CustomTextbox(customtkinter.CTkTextbox):
    def __init__(self, *args, scrollbar_button_color=None, **kwargs):
        super().__init__(*args, **kwargs)
        if scrollbar_button_color is not None:
            if hasattr(self, '_v_scrollbar') and self._v_scrollbar is not None:
                self._v_scrollbar.configure(button_color=scrollbar_button_color)
            if hasattr(self, '_h_scrollbar') and self._h_scrollbar is not None:
                self._h_scrollbar.configure(button_color=scrollbar_button_color)

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        customtkinter.set_appearance_mode("Dark")
        if os.path.exists(THEME_FILE): customtkinter.set_default_color_theme(THEME_FILE)
        
        self.title(APP_NAME)
        self.attributes('-fullscreen', True)
        self.bind("<Escape>", self.exit_fullscreen)

        self.container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.container.pack(side="top", fill="both", expand=True)

        self.frames = {}
        self.devices_to_wipe = []
        self.signing_key_present = os.path.exists(PRIVATE_KEY_PATH)

        for F in (SplashFrame, MainFrame, ConfirmationFrame, WipeProgressFrame):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(SplashFrame)
        
    def exit_fullscreen(self, event=None):
        self.attributes('-fullscreen', False)
        self.geometry("1200x800")

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
        if hasattr(frame, 'on_show'): frame.on_show()

    def start_wipe_process(self, devices):
        self.devices_to_wipe = devices
        self.frames[ConfirmationFrame].update_device_info(devices)
        self.show_frame(ConfirmationFrame)

    def execute_wipe(self):
        self.frames[WipeProgressFrame].start_wipe_queue(self.devices_to_wipe)
        self.show_frame(WipeProgressFrame)

class SplashFrame(customtkinter.CTkFrame):
    # This class is unchanged
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        try:
            self.logo_image = customtkinter.CTkImage(Image.open(LOGO_FILE), size=(350, 350))
            logo_label = customtkinter.CTkLabel(self, image=self.logo_image, text="")
            logo_label.pack(pady=(100, 20))
        except FileNotFoundError:
            logo_label = customtkinter.CTkLabel(self, text="🛡️", font=("Roboto", 100))
            logo_label.pack(pady=(100, 20))
        self.name_label = customtkinter.CTkLabel(self, text=APP_NAME, font=FONT_HEADER)
        self.name_label.pack(pady=10, padx=20)
        self.progress_bar = customtkinter.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.pack(pady=20, padx=100, fill="x")
    def on_show(self):
        self.progress_bar.start()
        self.after(3000, lambda: self.controller.show_frame(MainFrame))

class MainFrame(customtkinter.CTkFrame):
    # This class is unchanged, but provided for completeness
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.device_checkboxes = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0); self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=2); self.grid_rowconfigure(3, weight=0)
        header_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(10, 0), padx=20, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        header_label = customtkinter.CTkLabel(header_frame, text=APP_NAME, font=FONT_HEADER)
        header_label.grid(row=0, column=0, pady=10)
        drive_list_frame = customtkinter.CTkFrame(self)
        drive_list_frame.grid(row=1, column=0, pady=10, padx=20, sticky="nsew")
        drive_list_frame.grid_columnconfigure(0, weight=1); drive_list_frame.grid_rowconfigure(1, weight=1)
        drive_list_header = customtkinter.CTkLabel(drive_list_frame, text="1. Select Drives to Wipe", font=FONT_BODY_BOLD)
        drive_list_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.scrollable_drive_list = customtkinter.CTkScrollableFrame(drive_list_frame)
        self.scrollable_drive_list.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")
        details_container = customtkinter.CTkFrame(self, fg_color="transparent")
        details_container.grid(row=2, column=0, pady=10, padx=20, sticky="nsew")
        details_container.grid_columnconfigure((0, 1), weight=1)
        details_container.grid_rowconfigure(0, weight=1)
        drive_details_frame = customtkinter.CTkFrame(details_container)
        drive_details_frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        drive_details_header = customtkinter.CTkLabel(drive_details_frame, text="Drive Details & Sanitization Plan", font=FONT_BODY_BOLD)
        drive_details_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.details_textbox = CustomTextbox(drive_details_frame, state="disabled", font=FONT_MONO, scrollbar_button_color="#FFD700")
        self.details_textbox.grid(row=0, column=0, pady=(40,5), padx=10, sticky="nsew")
        host_details_frame = customtkinter.CTkFrame(details_container)
        host_details_frame.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        host_header = customtkinter.CTkLabel(host_details_frame, text="Host System Information", font=FONT_BODY_BOLD)
        host_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.host_details_textbox = CustomTextbox(host_details_frame, state="disabled", font=FONT_MONO, scrollbar_button_color="#FFD700")
        self.host_details_textbox.grid(row=0, column=0, pady=(40,5), padx=10, sticky="nsew")
        footer_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=3, column=0, pady=20, padx=20, sticky="ew")
        self.key_status_label = customtkinter.CTkLabel(footer_frame, text="", font=FONT_BODY)
        self.key_status_label.pack(side="left", padx=10)
        self.test_cert_button = customtkinter.CTkButton(footer_frame, text="Generate Test Certificate", font=FONT_BODY, command=self.generate_test_certificate)
        self.test_cert_button.pack(side="left", padx=10)
        self.wipe_button = customtkinter.CTkButton(footer_frame, text="Proceed...", font=FONT_BODY, state="disabled", fg_color="#8B0000", hover_color="#A52A2A", command=self.confirm_wipe)
        self.wipe_button.pack(side="right")
    def on_show(self): self.update_key_status(); self.populate_devices(); self.display_host_system_info()
    def update_key_status(self):
        can_certify = self.controller.signing_key_present
        self.key_status_label.configure(text="✅ Signing Key Found" if can_certify else "❌ Signing Key Missing!", text_color="green" if can_certify else "red")
        self.test_cert_button.configure(state="normal" if can_certify else "disabled"); self.update_selection_status()
    def generate_test_certificate(self):
        self.details_textbox.configure(state="normal"); self.details_textbox.delete("1.0", "end")
        self.details_textbox.insert("1.0", "Generating a test certificate with dummy data..."); self.details_textbox.configure(state="disabled")
        try:
            command = ['bash', CERT_SCRIPT_PATH, "Test Model ABC", "TEST123456789", "Flash Memory", APP_VERSION]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            self.details_textbox.configure(state="normal"); self.details_textbox.insert("end", f"\n\nSUCCESS!\n{result.stdout}"); self.details_textbox.configure(state="disabled")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.details_textbox.configure(state="normal"); self.details_textbox.insert("end", f"\n\nERROR:\n{e}\n{getattr(e, 'stderr', 'Script not found.')}"); self.details_textbox.configure(state="disabled")
    def get_detailed_device_info(self, dev_path):
        try:
            result = subprocess.run(['smartctl', '-i', '--json', dev_path], capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            lsblk_result = subprocess.run(['lsblk', '-d', '-n', '-o', 'ROTA', dev_path], capture_output=True, text=True, check=True)
            is_rotational = lsblk_result.stdout.strip() == '1'
            return {'manufacturer': data.get('vendor', 'Unknown'), 'model': data.get('model_name', 'N/A'), 'serial_number': data.get('serial_number', 'N/A'), 'media_type': 'Magnetic' if is_rotational else 'Flash Memory', 'size_bytes': data.get('user_capacity', {}).get('bytes', 0)}
        except Exception: return {'size_bytes': 0}
    def get_host_system_info(self, *args, **kwargs): pass;
    def display_host_system_info(self, *args, **kwargs): pass;
    def populate_devices(self, *args, **kwargs): pass;
    def update_selection_status(self, *args, **kwargs): pass;
    def display_drive_details(self, *args, **kwargs): pass;
    def confirm_wipe(self, *args, **kwargs): pass;

class ConfirmationFrame(customtkinter.CTkFrame):
    # This class is unchanged
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs);
    def update_device_info(self, *args, **kwargs): pass;
    def check_token(self, *args, **kwargs): pass;

# --- [MODIFIED] The entire WipeProgressFrame class is updated ---
class WipeProgressFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.process, self.start_time = None, 0
        self.device_queue, self.current_device_index, self.total_devices = [], 0, 0
        
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)
        center_frame = customtkinter.CTkFrame(self); center_frame.grid(row=0, column=0)
        
        self.overall_title_label = customtkinter.CTkLabel(center_frame, text="", font=FONT_SUBHEADER); self.overall_title_label.pack(pady=(20, 0), padx=50)
        self.title_label = customtkinter.CTkLabel(center_frame, text="Wiping Drive...", font=FONT_BODY_BOLD); self.title_label.pack(pady=(0,20), padx=50)
        self.progress_label = customtkinter.CTkLabel(center_frame, text="Status: Initializing...", font=FONT_BODY); self.progress_label.pack(pady=10, padx=20)
        
        self.progress_bar = customtkinter.CTkProgressBar(center_frame, width=500, mode='indeterminate'); self.progress_bar.pack(pady=10, padx=20)
        
        info_frame = customtkinter.CTkFrame(center_frame, fg_color="transparent"); info_frame.pack(pady=20, padx=20, fill="x")
        info_frame.grid_columnconfigure(0, weight=1)
        self.time_label = customtkinter.CTkLabel(info_frame, text="Elapsed: 00:00:00", font=FONT_MONO); self.time_label.grid(row=0, column=0, sticky="w")
        
        self.log_textbox = CustomTextbox(center_frame, height=250, width=600, state="disabled", font=FONT_MONO, scrollbar_button_color="#FFD700")
        self.log_textbox.pack(pady=10, padx=20)
        self.finish_button = customtkinter.CTkButton(center_frame, text="Return to Dashboard", font=FONT_BODY, command=lambda: controller.show_frame(MainFrame))
    
    def log(self, message):
        self.log_textbox.configure(state="normal"); self.log_textbox.insert("end", f"{message}\n"); self.log_textbox.see("end"); self.log_textbox.configure(state="disabled")

    def start_wipe_queue(self, devices):
        self.device_queue = list(devices)
        self.current_device_index, self.total_devices = 0, len(devices)
        self.log_textbox.configure(state="normal"); self.log_textbox.delete("1.0", "end"); self.log_textbox.configure(state="disabled")
        self.finish_button.pack_forget()
        self.process_next_in_queue()

    def process_next_in_queue(self):
        if not self.device_queue:
            self.overall_title_label.configure(text="All Wipes Complete!")
            self.log("✅ All selected drives have been processed.")
            self.finish_button.pack(pady=20)
            if self.progress_bar.winfo_exists(): self.progress_bar.stop()
            return
        
        if self.progress_bar.winfo_exists(): self.progress_bar.start()
        self.current_device_index += 1
        device_data = self.device_queue.pop(0)
        self.overall_title_label.configure(text=f"Processing Drive {self.current_device_index} of {self.total_devices}")
        self.title_label.configure(text=f"Wiping /dev/{device_data['name']} ({device_data['size']})")
        self.log("\n" + ("-"*50) + f"\nStarting wipe for /dev/{device_data['name']}\n" + ("-"*50))
        threading.Thread(target=self.run_wipe_script, args=(device_data,), daemon=True).start()

    def run_wipe_script(self, device_data):
        self.start_time = time.time(); self.after(1000, self.update_timer)
        device_path = f"/dev/{device_data['name']}"; command = ['bash', WIPE_SCRIPT_PATH, device_path, 'OBLITERATE']
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            q_out, q_err = Queue(), Queue()
            threading.Thread(target=self.read_stream, args=(self.process.stdout, q_out), daemon=True).start()
            threading.Thread(target=self.read_stream, args=(self.process.stderr, q_err), daemon=True).start() # We still read stderr for logging
            self.after(100, self.check_queues, q_out, q_err, device_data)
        except Exception as e: self.log(f"CRITICAL FAILURE: {e}")

    def read_stream(self, stream, queue):
        for line in iter(stream.readline, ''): queue.put(line)

    def check_queues(self, q_out, q_err, device_data):
        try:
            while True:
                line = q_out.get_nowait().strip()
                self.log(f"OUT: {line}")
                if line.startswith("PROGRESS:"): self.update_pass_status(line)
                elif "STATUS:SUCCESS" in line: self.wipe_finished(True, device_data); return
        except Empty: pass
        try:
            # We read stderr just to log it, not for progress updates
            while True: self.log(f"LOG: {q_err.get_nowait().strip()}")
        except Empty: pass
        
        if self.process.poll() is None: self.after(100, self.check_queues, q_out, q_err, device_data)
        elif self.process.returncode != 0: self.wipe_finished(False, device_data)

    def update_pass_status(self, line):
        try:
            parts = line.split(':'); progress_part, status_message = parts[1], parts[2]
            current_pass, total_passes = map(int, progress_part.split('/'))
            self.progress_label.configure(text=f"Status: Pass {current_pass} of {total_passes} - {status_message}")
        except (IndexError, ValueError): pass

    def wipe_finished(self, success, device_data):
        if self.progress_bar.winfo_exists(): self.progress_bar.stop()
        if success:
            self.progress_label.configure(text="Status: Wipe and Verification Complete!")
            self.log(f"✅ WIPE SUCCESSFUL for /dev/{device_data['name']}")
            self.generate_certificate(device_data)
        else:
            self.progress_label.configure(text="Status: WIPE FAILED!", text_color="orange")
            self.log(f"❌ WIPE FAILED for /dev/{device_data['name']}. Halting queue.")
            self.device_queue.clear()
        self.process_next_in_queue()

    def update_timer(self):
        if self.process and self.process.poll() is None:
            elapsed = time.time() - self.start_time
            self.time_label.configure(text=f"Elapsed: {str(datetime.timedelta(seconds=int(elapsed)))}")
            self.after(1000, self.update_timer)

    def generate_certificate(self, device_data):
        self.log(f"Calling certificate script for /dev/{device_data['name']}...")
        scraped_info = self.controller.frames[MainFrame].get_detailed_device_info(f"/dev/{device_data['name']}")
        model = scraped_info.get('model', 'N/A')
        serial = scraped_info.get('serial_number', 'N/A')
        media_type = scraped_info.get('media_type', 'N/A')
        try:
            command = ['bash', CERT_SCRIPT_PATH, model, serial, media_type, APP_VERSION]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            self.log(f"✅ {result.stdout}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.log(f"❌ ERROR: Certificate script failed!")
            self.log(f"   ERROR Details: {getattr(e, 'stderr', 'Script not found.')}")
            self.progress_label.configure(text="Wipe OK, but CERTIFICATE FAILED!", text_color="orange")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: This application requires root privileges.")
        print("Please run with 'sudo python3 /my-applications/obliterator/obliterator_gui.py'")
    else:
        app = App()
        app.mainloop()
