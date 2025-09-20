#!/usr/bin/env python3
# obliterator_gui.py - (Version 8.0 - Final UI & Multi-Drive Wipe)
# GUI for the Obliterator Secure Wipe Tool

import tkinter
import customtkinter
import subprocess
import json
import datetime
import os
import threading
import time
from queue import Queue, Empty

# --- Imports for the 'cryptography' library ---
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# --- Configuration ---
APP_NAME = "OBLITERATOR"
APP_VERSION = "8.0-final"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
THEME_FILE = os.path.join(SCRIPT_DIR, "purple_theme.json")
PRIVATE_KEY_PATH = os.path.join(SCRIPT_DIR, "keys/private_key.pem")
CERT_DIR = os.path.join(SCRIPT_DIR, "certificates/")
WIPE_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "wipe_disk.sh")

# --- [NEW] Font Definitions ---
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

# --- Main Application Controller ---
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        customtkinter.set_appearance_mode("Dark")
        if os.path.exists(THEME_FILE):
            customtkinter.set_default_color_theme(THEME_FILE)
        else:
            print(f"Warning: Theme file not found at {THEME_FILE}. Using default blue theme.")
        
        self.title(APP_NAME)
        self.geometry("1200x800")
        self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(0, weight=1)

        self.container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1); self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.certificate_data = {}
        self.devices_to_wipe = []

        for F in (SplashFrame, MainFrame, ConfirmationFrame, WipeProgressFrame):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(SplashFrame)

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
        if hasattr(frame, 'on_show'):
            frame.on_show()

    def start_wipe_process(self, devices, cert_data):
        self.devices_to_wipe = devices
        self.certificate_data = cert_data
        self.frames[ConfirmationFrame].update_device_info(devices)
        self.show_frame(ConfirmationFrame)

    def execute_wipe(self):
        self.frames[WipeProgressFrame].start_wipe_queue(self.devices_to_wipe, self.certificate_data)
        self.show_frame(WipeProgressFrame)

# --- Splash Screen Frame ---
class SplashFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.logo_label = customtkinter.CTkLabel(self, text="🛡️", font=("Roboto", 80))
        self.logo_label.pack(pady=(200, 0))
        self.name_label = customtkinter.CTkLabel(self, text=APP_NAME, font=FONT_HEADER)
        self.name_label.pack(pady=20, padx=20)
        self.progress_bar = customtkinter.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.pack(pady=10, padx=100, fill="x")
    def on_show(self):
        self.progress_bar.start()
        self.after(3000, lambda: self.controller.show_frame(MainFrame))

# --- Main Application Frame ---
class MainFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.device_checkboxes = {}
        self.form_widgets = {}

        self.grid_columnconfigure((0, 1), weight=1); self.grid_rowconfigure(2, weight=1)
        
        # --- [MODIFIED] Centered Header ---
        header_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, pady=10, padx=20, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        header_label = customtkinter.CTkLabel(header_frame, text=APP_NAME, font=FONT_HEADER)
        header_label.grid(row=0, column=0, pady=10)

        # Column 1: Device Selection
        drive_list_frame = customtkinter.CTkFrame(self)
        drive_list_frame.grid(row=1, column=0, rowspan=2, pady=10, padx=20, sticky="nsew")
        drive_list_frame.grid_columnconfigure(0, weight=1); drive_list_frame.grid_rowconfigure(1, weight=1)
        drive_list_header = customtkinter.CTkLabel(drive_list_frame, text="1. Select Device(s)", font=FONT_BODY_BOLD)
        drive_list_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.scrollable_drive_list = customtkinter.CTkScrollableFrame(drive_list_frame)
        self.scrollable_drive_list.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")
        
        # Column 2: Details and Form
        right_frame = customtkinter.CTkFrame(self)
        right_frame.grid(row=1, column=1, pady=10, padx=20, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1); right_frame.grid_rowconfigure(1, weight=1)
        
        details_header = customtkinter.CTkLabel(right_frame, text="Selected Device Details", font=FONT_BODY_BOLD)
        details_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.details_textbox = CustomTextbox(right_frame, state="disabled", font=FONT_MONO, scrollbar_button_color="#FFD700")
        self.details_textbox.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")

        form_frame = customtkinter.CTkFrame(self)
        form_frame.grid(row=2, column=1, pady=10, padx=20, sticky="nsew")
        form_frame.grid_columnconfigure(0, weight=1); form_frame.grid_rowconfigure(1, weight=1)
        
        form_header = customtkinter.CTkLabel(form_frame, text="2. Fill Certificate Details", font=FONT_BODY_BOLD)
        form_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.cert_form = customtkinter.CTkScrollableFrame(form_frame)
        self.cert_form.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")
        self.cert_form.grid_columnconfigure(1, weight=1)
        self.create_form_fields()

        # Footer
        footer_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=3, column=0, columnspan=2, pady=20, padx=20, sticky="e")
        self.wipe_button = customtkinter.CTkButton(footer_frame, text="Proceed to Final Confirmation...", font=FONT_BODY, state="disabled", fg_color="red", hover_color="darkred", command=self.confirm_wipe)
        self.wipe_button.pack()

    def on_show(self):
        self.populate_devices()

    def create_form_fields(self):
        media_fields = {
            "property_id": ("Entry", "Enter Asset Tag (if any)"),
            "media_source": ("Entry", "e.g., User Laptop, Server"),
            "sanitization_technique": ("Entry", "5-Pass Overwrite"),
            "verification_method": ("Option", ["Sampling", "Full", "None"]),
            "destination": ("Entry", "e.g., Reuse, Storage, Disposal")
        }
        for i, (key, (w_type, d_text)) in enumerate(media_fields.items()):
            label = customtkinter.CTkLabel(self.cert_form, text=key.replace('_', ' ').title(), font=FONT_BODY)
            label.grid(row=i, column=0, pady=5, padx=10, sticky="w")
            if w_type == "Entry":
                widget = customtkinter.CTkEntry(self.cert_form, placeholder_text=d_text, font=FONT_BODY)
                if key == "sanitization_technique": widget.insert(0, d_text)
            else:
                widget = customtkinter.CTkOptionMenu(self.cert_form, values=d_text, font=FONT_BODY)
            widget.grid(row=i, column=1, pady=5, padx=10, sticky="ew")
            self.form_widgets[key] = widget

    def get_detailed_device_info(self, dev_path):
        try:
            result = subprocess.run(['smartctl', '-i', '--json', dev_path], capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return {'model': data.get('model_name', 'N/A'), 'serial_number': data.get('serial_number', 'N/A')}
        except Exception: return {}

    def populate_devices(self):
        for checkbox in self.device_checkboxes.values(): checkbox.destroy()
        self.device_checkboxes.clear()
        try:
            result = subprocess.run(['lsblk', '-d', '--json', '-o', 'NAME,MODEL,SERIAL,SIZE,TYPE'], capture_output=True, text=True, check=True)
            devices = [dev for dev in json.loads(result.stdout).get("blockdevices", []) if dev.get("type") in ["disk", "nvme"]]
        except Exception: devices = []
        for dev in devices:
            dev_path = f"/dev/{dev.get('name', 'N/A')}"
            display_text = f"💾 {dev_path}  ({dev.get('size', 'N/A')})"
            var = tkinter.BooleanVar()
            checkbox = customtkinter.CTkCheckBox(self.scrollable_drive_list, text=display_text, variable=var, font=FONT_BODY, command=self.update_selection_status)
            checkbox.pack(anchor="w", padx=10, pady=5)
            self.device_checkboxes[dev_path] = {"var": var, "data": dev}
        self.update_selection_status()

    def update_selection_status(self):
        selected_devs_data = [info["data"] for path, info in self.device_checkboxes.items() if info["var"].get()]
        self.wipe_button.configure(state="normal" if selected_devs_data else "disabled")
        self.display_drive_details(selected_devs_data)

    def display_drive_details(self, selected_devs):
        self.details_textbox.configure(state="normal")
        self.details_textbox.delete("1.0", "end")
        if not selected_devs:
            self.details_textbox.insert("1.0", "Select one or more drives to begin.")
        else:
            details_text = f"{len(selected_devs)} DEVICE(S) SELECTED:\n" + ("-"*40) + "\n"
            for dev_data in selected_devs:
                dev_path = f"/dev/{dev_data.get('name')}"
                scraped = self.get_detailed_device_info(dev_path)
                details_text += (f"Device: {dev_path} ({dev_data.get('size')})\n"
                                 f"Model:  {scraped.get('model')}\n"
                                 f"Serial: {scraped.get('serial_number')}\n\n")
            self.details_textbox.insert("1.0", details_text)
        self.details_textbox.configure(state="disabled")

    def confirm_wipe(self):
        selected_devices = [info["data"] for path, info in self.device_checkboxes.items() if info["var"].get()]
        cert_data = {key: widget.get() for key, widget in self.form_widgets.items()}
        self.controller.start_wipe_process(selected_devices, cert_data)

class ConfirmationFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.main_label = customtkinter.CTkLabel(self, text="⚠️ FINAL CONFIRMATION ⚠️", font=FONT_HEADER, text_color="orange")
        self.main_label.pack(pady=(200, 20))
        self.info_label = customtkinter.CTkLabel(self, text="", font=FONT_BODY, wraplength=500)
        self.info_label.pack(pady=10, padx=20)
        self.instruction_label = customtkinter.CTkLabel(self, text="Type 'OBLITERATE' below to proceed.", font=FONT_BODY)
        self.instruction_label.pack(pady=20)
        self.entry = customtkinter.CTkEntry(self, width=300, font=FONT_SUBHEADER)
        self.entry.pack()
        self.entry.bind("<KeyRelease>", self.check_token)
        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=40)
        self.confirm_button = customtkinter.CTkButton(button_frame, text="Confirm and Wipe", font=FONT_BODY, state="disabled", fg_color="red", hover_color="darkred", command=self.controller.execute_wipe)
        self.confirm_button.pack(side="left", padx=10)
        cancel_button = customtkinter.CTkButton(button_frame, text="Cancel", font=FONT_BODY, command=lambda: self.controller.show_frame(MainFrame))
        cancel_button.pack(side="right", padx=10)
    def update_device_info(self, devices):
        info_text = f"You are about to permanently destroy all data on {len(devices)} device(s):\n\n"
        for dev in devices[:3]: # show up to 3 devices
            info_text += f"- /dev/{dev.get('name')} ({dev.get('model') or 'N/A'})\n"
        if len(devices) > 3:
            info_text += f"...and {len(devices)-3} more."
        self.info_label.configure(text=info_text)
        self.entry.delete(0, "end"); self.check_token(None)
    def check_token(self, event):
        self.confirm_button.configure(state="normal" if self.entry.get() == "OBLITERATE" else "disabled")

class WipeProgressFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.process, self.start_time, self.cert_data = None, 0, {}
        self.device_queue = []
        self.current_device_index = 0
        self.total_devices = 0

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)
        center_frame = customtkinter.CTkFrame(self); center_frame.grid(row=0, column=0)
        self.overall_title_label = customtkinter.CTkLabel(center_frame, text="", font=FONT_SUBHEADER); self.overall_title_label.pack(pady=(20, 0), padx=50)
        self.title_label = customtkinter.CTkLabel(center_frame, text="Wiping Drive...", font=FONT_BODY_BOLD); self.title_label.pack(pady=(0,20), padx=50)
        self.progress_label = customtkinter.CTkLabel(center_frame, text="Status: Initializing...", font=FONT_BODY); self.progress_label.pack(pady=10, padx=20)
        self.progress_bar = customtkinter.CTkProgressBar(center_frame, width=500); self.progress_bar.set(0); self.progress_bar.pack(pady=10, padx=20)
        info_frame = customtkinter.CTkFrame(center_frame, fg_color="transparent"); info_frame.pack(pady=20, padx=20, fill="x"); info_frame.grid_columnconfigure((0, 1), weight=1)
        self.time_label = customtkinter.CTkLabel(info_frame, text="Elapsed Time: 00:00:00", font=FONT_MONO); self.time_label.grid(row=0, column=0, sticky="w")
        self.speed_label = customtkinter.CTkLabel(info_frame, text="Throughput: 0 MB/s", font=FONT_MONO); self.speed_label.grid(row=0, column=1, sticky="e")
        self.log_textbox = CustomTextbox(center_frame, height=250, width=600, state="disabled", font=FONT_MONO, scrollbar_button_color="#FFD700")
        self.log_textbox.pack(pady=10, padx=20)
        self.finish_button = customtkinter.CTkButton(center_frame, text="Return to Dashboard", font=FONT_BODY, command=lambda: controller.show_frame(MainFrame))
    
    def log(self, message):
        self.log_textbox.configure(state="normal"); self.log_textbox.insert("end", f"{message}\n"); self.log_textbox.see("end"); self.log_textbox.configure(state="disabled")

    def start_wipe_queue(self, devices, cert_data):
        self.device_queue = list(devices)
        self.cert_data = cert_data
        self.current_device_index = 0
        self.total_devices = len(devices)
        self.log_textbox.configure(state="normal"); self.log_textbox.delete("1.0", "end"); self.log_textbox.configure(state="disabled")
        self.finish_button.pack_forget()
        self.process_next_in_queue()

    def process_next_in_queue(self):
        if not self.device_queue:
            self.overall_title_label.configure(text="All Wipes Complete!")
            self.log("✅ All selected drives have been processed.")
            self.finish_button.pack(pady=20)
            return

        self.current_device_index += 1
        device_data = self.device_queue.pop(0)
        
        self.progress_bar.set(0)
        self.overall_title_label.configure(text=f"Processing Drive {self.current_device_index} of {self.total_devices}")
        self.title_label.configure(text=f"Wiping /dev/{device_data['name']}")
        self.log("\n" + ("-"*50) + f"\nStarting wipe for /dev/{device_data['name']}\n" + ("-"*50))
        
        threading.Thread(target=self.run_wipe_script, args=(device_data,), daemon=True).start()

    def run_wipe_script(self, device_data):
        self.start_time = time.time(); self.after(1000, self.update_timer)
        device_path = f"/dev/{device_data['name']}"; command = ['bash', WIPE_SCRIPT_PATH, device_path, 'OBLITERATE']
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            q_out, q_err = Queue(), Queue()
            threading.Thread(target=self.read_stream, args=(self.process.stdout, q_out), daemon=True).start()
            threading.Thread(target=self.read_stream, args=(self.process.stderr, q_err), daemon=True).start()
            self.after(100, self.check_queues, q_out, q_err, device_data)
        except Exception as e: self.log(f"CRITICAL FAILURE: {e}")

    def read_stream(self, stream, queue):
        for line in iter(stream.readline, ''): queue.put(line)

    def check_queues(self, q_out, q_err, device_data):
        try:
            while True:
                line = q_out.get_nowait().strip()
                self.log(f"OUT: {line}")
                if line.startswith("PROGRESS:"): self.update_progress_from_line(line)
                elif "STATUS:SUCCESS" in line: self.wipe_finished(True, device_data); return
        except Empty: pass
        try:
            while True:
                line = q_err.get_nowait().strip()
                if "MB/s" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "MB/s" in part: self.speed_label.configure(text=f"Throughput: {parts[i-1] if i > 0 else '?'} MB/s"); break
                else: self.log(f"ERR: {line}")
        except Empty: pass
        if self.process.poll() is None: self.after(100, self.check_queues, q_out, q_err, device_data)
        elif self.process.returncode != 0: self.wipe_finished(False, device_data)

    def update_progress_from_line(self, line):
        try:
            parts = line.split(':'); progress_part, status_message = parts[1], parts[2]
            current_pass, total_passes = map(int, progress_part.split('/'))
            self.progress_bar.set(float(current_pass) / float(total_passes))
            self.progress_label.configure(text=f"Status: Pass {current_pass}/{total_passes} - {status_message}")
        except (IndexError, ValueError): pass

    def wipe_finished(self, success, device_data):
        self.progress_bar.set(1.0)
        if success:
            self.progress_label.configure(text="Status: Wipe and Verification Complete!")
            self.log(f"✅ WIPE SUCCESSFUL for /dev/{device_data['name']}")
            self.generate_certificate(device_data)
        else:
            self.progress_label.configure(text="Status: WIPE FAILED!", text_color="red")
            self.log(f"❌ WIPE FAILED for /dev/{device_data['name']}. Check logs. Skipping remaining drives.")
            self.device_queue.clear() # Stop processing further drives on failure
        
        self.process_next_in_queue()

    def update_timer(self):
        if self.process and self.process.poll() is None:
            elapsed = time.time() - self.start_time
            self.time_label.configure(text=f"Elapsed Time: {str(datetime.timedelta(seconds=int(elapsed)))}")
            self.after(1000, self.update_timer)

    def generate_certificate(self, device_data):
        self.log(f"Generating certificate for /dev/{device_data['name']}...")
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        scraped_info = self.controller.frames[MainFrame].get_detailed_device_info(f"/dev/{device_data['name']}")
        serial = scraped_info.get('serial_number') or 'UNKNOWN_SERIAL'
        
        cert_payload = {
            "nist_reference": "NIST SP 800-88r2 IPD July 2025", "tool_information": {"name": APP_NAME, "version": APP_VERSION},
            "sanitization_event": {"timestamp": timestamp.isoformat(), "status": "Success", "technique": self.cert_data.get('sanitization_technique')},
            "media_information": {
                "manufacturer": scraped_info.get('manufacturer'), "model": scraped_info.get('model'), "serial_number": serial,
                "property_id": self.cert_data.get('property_id'), "media_type": scraped_info.get('media_type'),
                "media_source": self.cert_data.get('media_source'), "destination": self.cert_data.get('destination')
            },
            "verification": {"method": self.cert_data.get('verification_method'), "timestamp": timestamp.isoformat(), "status": "Passed"}
        }
        try:
            with open(PRIVATE_KEY_PATH, 'rb') as f: private_key = serialization.load_pem_private_key(f.read(), password=None)
            json_payload_bytes = json.dumps(cert_payload, sort_keys=True, indent=2).encode('utf-8')
            signature = private_key.sign(json_payload_bytes, padding.PKCS1v15(), hashes.SHA256())
            signed_cert_container = {"certificate_payload": cert_payload, "signature": base64.b64encode(signature).decode('utf-8')}
            filename = f"wipe-{timestamp.strftime('%Y%m%d-%H%M%S')}-{serial}.json"; filepath = os.path.join(CERT_DIR, filename)
            if not os.path.exists(CERT_DIR): os.makedirs(CERT_DIR)
            with open(filepath, 'w') as f: json.dump(signed_cert_container, f, indent=2)
            self.log(f"✅ Certificate saved successfully to {filepath}")
        except Exception as e: self.log(f"❌ ERROR: Could not sign or save certificate: {e}")

# --- Entry Point ---
if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: This application requires root privileges.")
        print("Please run with 'sudo python3 obliterator_gui.py'")
    else:
        app = App()
        app.mainloop()
