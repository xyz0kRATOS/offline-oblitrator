#!/usr/bin/env python3
# obliterator_gui.py - (Version 5.0 - NIST Form & Purple Theme)
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
APP_NAME = "Obliterator"
APP_VERSION = "5.0-final"
THEME_FILE = "purple_theme.json" # New custom theme
PRIVATE_KEY_PATH = "/mnt/home/obliterator/keys/private_key.pem"
CERT_DIR = "/mnt/home/obliterator/certificates/"
WIPE_SCRIPT_PATH = "/mnt/home/obliterator/wipe_disk.sh"

# --- Main Application Controller ---
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        customtkinter.set_appearance_mode("Dark")
        if os.path.exists(THEME_FILE):
            customtkinter.set_default_color_theme(THEME_FILE)
        
        self.title(APP_NAME)
        self.geometry("1200x800") # Increased size for new form

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.certificate_data = {}

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
        self.certificate_data = cert_data
        self.certificate_data['device'] = devices[0]
        self.frames[ConfirmationFrame].update_device_info(devices)
        self.show_frame(ConfirmationFrame)

    def execute_wipe(self):
        self.frames[WipeProgressFrame].prepare_for_wipe(self.certificate_data)
        self.show_frame(WipeProgressFrame)

# --- Splash Screen Frame ---
class SplashFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.logo_label = customtkinter.CTkLabel(self, text="🛡️", font=("Roboto", 80))
        self.logo_label.pack(pady=(200, 0))
        self.name_label = customtkinter.CTkLabel(self, text=APP_NAME, font=("Roboto", 50, "bold"))
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

        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header_label = customtkinter.CTkLabel(self, text="Obliterator Dashboard", font=("Roboto", 24, "bold"))
        header_label.grid(row=0, column=0, columnspan=3, pady=20, padx=20, sticky="w")

        # Column 1: Device Selection
        drive_list_frame = customtkinter.CTkFrame(self)
        drive_list_frame.grid(row=1, column=0, pady=10, padx=20, sticky="nsew")
        drive_list_frame.grid_rowconfigure(1, weight=1)
        drive_list_frame.grid_columnconfigure(0, weight=1)
        drive_list_header = customtkinter.CTkLabel(drive_list_frame, text="1. Select Device", font=("Roboto", 16, "bold"))
        drive_list_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.scrollable_drive_list = customtkinter.CTkScrollableFrame(drive_list_frame)
        self.scrollable_drive_list.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")

        # Column 2: Certificate & Operator Information Form
        form_frame = customtkinter.CTkFrame(self)
        form_frame.grid(row=1, column=1, pady=10, padx=10, sticky="nsew")
        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_rowconfigure(1, weight=1)
        form_header = customtkinter.CTkLabel(form_frame, text="2. Enter Certificate Details", font=("Roboto", 16, "bold"))
        form_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.cert_form = customtkinter.CTkScrollableFrame(form_frame)
        self.cert_form.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")
        self.cert_form.grid_columnconfigure(1, weight=1)
        self.create_form_fields()

        # Column 3: Drive Details & Action
        action_frame = customtkinter.CTkFrame(self)
        action_frame.grid(row=1, column=2, pady=10, padx=20, sticky="nsew")
        action_frame.grid_rowconfigure(1, weight=1)
        action_frame.grid_columnconfigure(0, weight=1)
        details_header = customtkinter.CTkLabel(action_frame, text="3. Review & Wipe", font=("Roboto", 16, "bold"))
        details_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        self.details_textbox = customtkinter.CTkTextbox(action_frame, state="disabled", font=("monospace", 12))
        self.details_textbox.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")
        
        self.refresh_button = customtkinter.CTkButton(action_frame, text="Refresh Devices", command=self.populate_devices)
        self.refresh_button.grid(row=2, column=0, pady=10, padx=10, sticky="ew")
        self.wipe_button = customtkinter.CTkButton(action_frame, text="Proceed to Wipe...", state="disabled", fg_color="red", hover_color="darkred", command=self.confirm_wipe)
        self.wipe_button.grid(row=3, column=0, pady=10, padx=10, sticky="ew")

    def on_show(self):
        self.populate_devices()

    def create_form_fields(self):
        fields = {
            "Media Details": {
                "manufacturer": ("Entry", ""), "model": ("Entry", ""), "serial_number": ("Entry", ""),
                "property_id": ("Entry", "Optional"),
                "media_type": ("Option", ["Magnetic", "Flash Memory", "Hybrid"]),
                "media_source": ("Entry", "e.g., User PC, Server")
            },
            "Sanitization Plan": {
                "sanitization_method": ("Option", ["Clear", "Purge", "Destroy"]),
                "sanitization_technique": ("Entry", "e.g., 5-Pass Overwrite"),
                "tool_used": ("Entry", f"{APP_NAME} v{APP_VERSION}"),
                "verification_method": ("Option", ["Full", "Sampling", "None"]),
                "destination": ("Entry", "e.g., Reuse, Storage, Disposal")
            },
            "Operator Details": {
                "operator_name": ("Entry", ""), "operator_title": ("Entry", ""),
                "operator_location": ("Entry", ""), "operator_contact": ("Entry", ""),
                "operator_signature": ("Entry", "Type full name to sign")
            }
        }
        row = 0
        for section, items in fields.items():
            section_label = customtkinter.CTkLabel(self.cert_form, text=section, font=("Roboto", 14, "bold"))
            section_label.grid(row=row, column=0, columnspan=2, pady=(15, 5), padx=10, sticky="w")
            row += 1
            for key, (widget_type, default) in items.items():
                label = customtkinter.CTkLabel(self.cert_form, text=key.replace('_', ' ').title())
                label.grid(row=row, column=0, pady=5, padx=10, sticky="w")
                if widget_type == "Entry":
                    widget = customtkinter.CTkEntry(self.cert_form, placeholder_text=default)
                    if key == "tool_used":
                        widget.insert(0, default)
                else: # OptionMenu
                    widget = customtkinter.CTkOptionMenu(self.cert_form, values=default)
                widget.grid(row=row, column=1, pady=5, padx=10, sticky="ew")
                self.form_widgets[key] = widget
                row += 1

    def populate_devices(self):
        for checkbox in self.device_checkboxes.values():
            checkbox.destroy()
        self.device_checkboxes.clear()
        
        try:
            result = subprocess.run(['lsblk', '-d', '--json', '-o', 'NAME,MODEL,SERIAL,SIZE,TYPE'], capture_output=True, text=True, check=True)
            devices = [dev for dev in json.loads(result.stdout).get("blockdevices", []) if dev.get("type") in ["disk", "nvme"]]
        except Exception:
            devices = []

        for dev in devices:
            dev_path = f"/dev/{dev.get('name', 'N/A')}"
            display_text = f"💾 {dev_path}  ({dev.get('size', 'N/A')})"
            var = tkinter.BooleanVar()
            checkbox = customtkinter.CTkCheckBox(self.scrollable_drive_list, text=display_text, variable=var, font=("Roboto", 14), command=self.update_selection_status)
            checkbox.pack(anchor="w", padx=10, pady=5)
            self.device_checkboxes[dev_path] = {"var": var, "data": dev, "widget": checkbox}
        self.update_selection_status()

    def update_selection_status(self):
        selected_devs = [info for path, info in self.device_checkboxes.items() if info["var"].get()]
        
        if len(selected_devs) == 1:
            self.wipe_button.configure(state="normal")
            self.display_drive_details(selected_devs[0]["data"])
        else:
            self.wipe_button.configure(state="disabled")
            self.display_drive_details(None, count=len(selected_devs))

    def display_drive_details(self, dev_data, count=1):
        self.details_textbox.configure(state="normal")
        self.details_textbox.delete("1.0", "end")
        if dev_data:
            details = (
                f"Device: /dev/{dev_data.get('name')}\n"
                f"Model:  {dev_data.get('model') or 'N/A'}\n"
                f"Serial: {dev_data.get('serial') or 'N/A'}\n"
                f"Size:   {dev_data.get('size') or 'N/A'}\n"
                f"Type:   {dev_data.get('type') or 'N/A'}\n"
            )
            self.details_textbox.insert("1.0", details)
            # Auto-fill form
            self.form_widgets['manufacturer'].delete(0, "end")
            self.form_widgets['model'].delete(0, "end"); self.form_widgets['model'].insert(0, dev_data.get('model') or '')
            self.form_widgets['serial_number'].delete(0, "end"); self.form_widgets['serial_number'].insert(0, dev_data.get('serial') or '')
        elif count > 1:
            self.details_textbox.insert("1.0", "Please select only ONE drive to wipe at a time.")
        else:
            self.details_textbox.insert("1.0", "Select a drive to view details and fill form.")
        self.details_textbox.configure(state="disabled")

    def confirm_wipe(self):
        selected_devices = [info["data"] for path, info in self.device_checkboxes.items() if info["var"].get()]
        
        cert_data = {}
        for key, widget in self.form_widgets.items():
            cert_data[key] = widget.get()
            
        self.controller.start_wipe_process(selected_devices, cert_data)

# ... [ConfirmationFrame and WipeProgressFrame remain largely the same, but WipeProgressFrame needs to handle cert data]
# --- Confirmation Frame ---
class ConfirmationFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.main_label = customtkinter.CTkLabel(self, text="⚠️ FINAL CONFIRMATION ⚠️", font=("Roboto", 36, "bold"), text_color="orange")
        self.main_label.pack(pady=(200, 20))

        self.info_label = customtkinter.CTkLabel(self, text="This will permanently destroy all data.", font=("Roboto", 16), wraplength=450)
        self.info_label.pack(pady=10, padx=20)

        self.instruction_label = customtkinter.CTkLabel(self, text="Type 'OBLITERATE' below to proceed.", font=("Roboto", 14))
        self.instruction_label.pack(pady=20)
        
        self.entry = customtkinter.CTkEntry(self, width=250, font=("Roboto", 16))
        self.entry.pack()
        self.entry.bind("<KeyRelease>", self.check_token)

        button_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=40)
        
        self.confirm_button = customtkinter.CTkButton(button_frame, text="Confirm and Wipe", state="disabled", fg_color="red", hover_color="darkred", command=self.controller.execute_wipe)
        self.confirm_button.pack(side="left", padx=10)
        
        cancel_button = customtkinter.CTkButton(button_frame, text="Cancel", command=lambda: self.controller.show_frame(MainFrame))
        cancel_button.pack(side="right", padx=10)

    def update_device_info(self, devices):
        dev = devices[0]
        info_text = (
            f"You are about to permanently destroy all data on:\n\n"
            f"Device: /dev/{dev.get('name')}\n"
            f"Model: {dev.get('model') or 'N/A'}\n"
            f"Size: {dev.get('size') or 'N/A'}"
        )
        self.info_label.configure(text=info_text)
        self.entry.delete(0, "end")
        self.check_token(None)

    def check_token(self, event):
        self.confirm_button.configure(state="normal" if self.entry.get() == "OBLITERATE" else "disabled")

# --- Wipe Progress Frame ---
class WipeProgressFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.process = None
        self.start_time = 0
        self.cert_data = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        center_frame = customtkinter.CTkFrame(self)
        center_frame.grid(row=0, column=0)

        self.title_label = customtkinter.CTkLabel(center_frame, text="Wiping Drive...", font=("Roboto", 28, "bold"))
        self.title_label.pack(pady=20, padx=50)

        self.progress_label = customtkinter.CTkLabel(center_frame, text="Status: Initializing...", font=("Roboto", 14))
        self.progress_label.pack(pady=10, padx=20)
        
        self.progress_bar = customtkinter.CTkProgressBar(center_frame, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10, padx=20)

        info_frame = customtkinter.CTkFrame(center_frame, fg_color="transparent")
        info_frame.pack(pady=20, padx=20, fill="x")
        info_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.time_label = customtkinter.CTkLabel(info_frame, text="Elapsed Time: 00:00:00", font=("monospace", 12))
        self.time_label.grid(row=0, column=0, sticky="w")
        self.speed_label = customtkinter.CTkLabel(info_frame, text="Throughput: 0 MB/s", font=("monospace", 12))
        self.speed_label.grid(row=0, column=1, sticky="e")

        self.log_textbox = customtkinter.CTkTextbox(center_frame, height=200, width=500, state="disabled")
        self.log_textbox.pack(pady=10, padx=20)
        
        self.finish_button = customtkinter.CTkButton(center_frame, text="Return to Dashboard", command=lambda: controller.show_frame(MainFrame))

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def prepare_for_wipe(self, cert_data):
        self.cert_data = cert_data
        device_data = self.cert_data['device']
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        self.progress_bar.set(0)
        self.finish_button.pack_forget()
        self.title_label.configure(text=f"Wiping /dev/{device_data['name']}")
        threading.Thread(target=self.run_wipe_script, args=(device_data,), daemon=True).start()

    def run_wipe_script(self, device_data):
        self.start_time = time.time()
        self.after(1000, self.update_timer)
        device_path = f"/dev/{device_data['name']}"
        command = ['bash', WIPE_SCRIPT_PATH, device_path, 'OBLITERATE']
        
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            q_out, q_err = Queue(), Queue()
            threading.Thread(target=self.read_stream, args=(self.process.stdout, q_out), daemon=True).start()
            threading.Thread(target=self.read_stream, args=(self.process.stderr, q_err), daemon=True).start()
            self.after(100, self.check_queues, q_out, q_err)
        except Exception as e:
            self.log(f"CRITICAL FAILURE: {e}")

    def read_stream(self, stream, queue):
        for line in iter(stream.readline, ''):
            queue.put(line)

    def check_queues(self, q_out, q_err):
        try:
            while True:
                line = q_out.get_nowait().strip()
                self.log(f"OUT: {line}")
                if line.startswith("PROGRESS:"):
                    self.update_progress_from_line(line)
                elif "STATUS:SUCCESS" in line:
                    self.wipe_finished(True)
                    return # Stop checking
        except Empty:
            pass

        try:
            while True:
                line = q_err.get_nowait().strip()
                if "MB/s" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "MB/s" in part:
                            speed = parts[i-1] if i > 0 else "?"
                            self.speed_label.configure(text=f"Throughput: {speed} MB/s")
                            break
                else:
                    self.log(f"ERR: {line}")
        except Empty:
            pass
        
        if self.process.poll() is None:
            self.after(100, self.check_queues, q_out, q_err)
        elif self.process.returncode != 0:
            self.wipe_finished(False)

    def update_progress_from_line(self, line):
        try:
            parts = line.split(':')
            progress_part, status_message = parts[1], parts[2]
            current_pass, total_passes = map(int, progress_part.split('/'))
            progress_value = float(current_pass) / float(total_passes)
            self.progress_bar.set(progress_value)
            self.progress_label.configure(text=f"Status: Pass {current_pass}/{total_passes} - {status_message}")
        except (IndexError, ValueError):
            pass

    def wipe_finished(self, success):
        self.progress_bar.set(1.0)
        if success:
            self.progress_label.configure(text="Status: Wipe and Verification Complete!")
            self.log("✅ WIPE SUCCESSFUL")
            self.generate_certificate()
        else:
            self.progress_label.configure(text="Status: WIPE FAILED!", text_color="red")
            self.log("❌ WIPE FAILED. Check logs for errors.")
        self.finish_button.pack(pady=20)

    def update_timer(self):
        if self.process and self.process.poll() is None:
            elapsed = time.time() - self.start_time
            self.time_label.configure(text=f"Elapsed Time: {str(datetime.timedelta(seconds=int(elapsed)))}")
            self.after(1000, self.update_timer)

    def generate_certificate(self):
        self.log("Generating sanitization certificate...")
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        device_data = self.cert_data.pop('device')
        serial = device_data.get('serial') or 'UNKNOWN_SERIAL'

        # Build the certificate from the form data
        cert_payload = {
            "nist_reference": "NIST SP 800-88r2 IPD July 2025",
            "tool_information": {"name": APP_NAME, "version": APP_VERSION},
            "sanitization_event": {
                "timestamp": timestamp.isoformat(),
                "status": "Success",
                "method": self.cert_data.get('sanitization_method'),
                "technique": self.cert_data.get('sanitization_technique')
            },
            "media_information": {
                "manufacturer": self.cert_data.get('manufacturer'),
                "model": self.cert_data.get('model'),
                "serial_number": self.cert_data.get('serial_number'),
                "property_id": self.cert_data.get('property_id'),
                "media_type": self.cert_data.get('media_type'),
                "media_source": self.cert_data.get('media_source'),
                "destination": self.cert_data.get('destination')
            },
            "verification": {
                "method": self.cert_data.get('verification_method'),
                "timestamp": timestamp.isoformat(),
                "status": "Passed"
            },
            "operator": {
                "name": self.cert_data.get('operator_name'),
                "title": self.cert_data.get('operator_title'),
                "location": self.cert_data.get('operator_location'),
                "contact": self.cert_data.get('operator_contact'),
                "signature": self.cert_data.get('operator_signature')
            }
        }
        
        try:
            with open(PRIVATE_KEY_PATH, 'rb') as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None)
            
            json_payload_bytes = json.dumps(cert_payload, sort_keys=True).encode('utf-8')
            signature = private_key.sign(json_payload_bytes, padding.PKCS1v15(), hashes.SHA256())
            
            signed_cert_container = {
                "certificate_payload": cert_payload,
                "signature": base64.b64encode(signature).decode('utf-8')
            }
            
            filename = f"wipe-{timestamp.strftime('%Y%m%d-%H%M%S')}-{serial}.json"
            filepath = os.path.join(CERT_DIR, filename)
            
            if not os.path.exists(CERT_DIR):
                os.makedirs(CERT_DIR)
                
            with open(filepath, 'w') as f:
                json.dump(signed_cert_container, f, indent=2)
                
            self.log(f"✅ Certificate saved successfully to {filepath}")
            
        except Exception as e:
            self.log(f"❌ ERROR: Could not sign or save certificate: {e}")

# --- Entry Point ---
if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: This application requires root privileges.")
        print("Please run with 'sudo python3 obliterator_gui.py'")
    else:
        app = App()
        app.mainloop()
