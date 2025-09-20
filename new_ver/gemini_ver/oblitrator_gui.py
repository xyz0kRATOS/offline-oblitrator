#!/usr/bin/env python3
# obliterator_gui.py - (Version 4.0 - Single-Window Redesign)
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

# --- Configuration ---
APP_NAME = "Obliterator"
APP_VERSION = "4.0-final"
THEME_COLOR = "dark-blue"
PRIVATE_KEY_PATH = "/mnt/home/obliterator/keys/private_key.pem"
CERT_DIR = "/mnt/home/obliterator/certificates/"
WIPE_SCRIPT_PATH = "/mnt/home/obliterator/wipe_disk.sh"

# --- Main Application Controller ---
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("850x650")
        customtkinter.set_appearance_mode("Dark")
        customtkinter.set_default_color_theme(THEME_COLOR)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.container = customtkinter.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.selected_devices_data = []

        for F in (SplashFrame, MainFrame, ConfirmationFrame, WipeProgressFrame):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(SplashFrame)

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
        # If the frame has an 'on_show' method, call it.
        if hasattr(frame, 'on_show'):
            frame.on_show()

    def start_wipe_process(self, devices):
        self.selected_devices_data = devices
        self.frames[ConfirmationFrame].update_device_info(devices)
        self.show_frame(ConfirmationFrame)

    def execute_wipe(self):
        self.frames[WipeProgressFrame].prepare_for_wipe(self.selected_devices_data[0])
        self.show_frame(WipeProgressFrame)

# --- Splash Screen Frame ---
class SplashFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.logo_label = customtkinter.CTkLabel(self, text="🛡️", font=("Roboto", 80))
        self.logo_label.pack(pady=(150, 0))

        self.name_label = customtkinter.CTkLabel(self, text=APP_NAME, font=("Roboto", 50, "bold"))
        self.name_label.pack(pady=20, padx=20)

        self.progress_bar = customtkinter.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.pack(pady=10, padx=100, fill="x")

    def on_show(self):
        """Called by the controller when this frame is shown."""
        self.progress_bar.start()
        # After 3 seconds, transition to the main frame
        self.after(3000, lambda: self.controller.show_frame(MainFrame))

# --- Main Application Frame ---
class MainFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.device_checkboxes = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header_label = customtkinter.CTkLabel(self, text="Select Drives to Obliterate", font=("Roboto", 24, "bold"))
        header_label.grid(row=0, column=0, columnspan=2, pady=20, padx=20, sticky="w")

        # Drive List Panel
        drive_list_frame = customtkinter.CTkFrame(self)
        drive_list_frame.grid(row=1, column=0, pady=10, padx=20, sticky="nsew")
        drive_list_frame.grid_rowconfigure(1, weight=1)
        drive_list_frame.grid_columnconfigure(0, weight=1)
        
        drive_list_header = customtkinter.CTkLabel(drive_list_frame, text="Available Devices", font=("Roboto", 16))
        drive_list_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        
        self.scrollable_drive_list = customtkinter.CTkScrollableFrame(drive_list_frame, label_text="")
        self.scrollable_drive_list.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")

        # Drive Details Panel
        drive_details_frame = customtkinter.CTkFrame(self)
        drive_details_frame.grid(row=1, column=1, pady=10, padx=(0, 20), sticky="nsew")
        drive_details_frame.grid_rowconfigure(1, weight=1)
        drive_details_frame.grid_columnconfigure(0, weight=1)
        
        details_header = customtkinter.CTkLabel(drive_details_frame, text="Drive Details", font=("Roboto", 16))
        details_header.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        
        self.details_textbox = customtkinter.CTkTextbox(drive_details_frame, state="disabled", font=("monospace", 12))
        self.details_textbox.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")

        # Footer / Action Buttons
        footer_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=2, column=0, columnspan=2, pady=20, padx=20, sticky="ew")
        
        self.refresh_button = customtkinter.CTkButton(footer_frame, text="Refresh Devices", command=self.populate_devices)
        self.refresh_button.pack(side="left")
        
        self.wipe_button = customtkinter.CTkButton(footer_frame, text="Wipe Selected...", state="disabled", fg_color="red", hover_color="darkred", command=self.confirm_wipe)
        self.wipe_button.pack(side="right")

    def on_show(self):
        self.populate_devices()

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
        selected_dev_paths = [path for path, info in self.device_checkboxes.items() if info["var"].get()]
        
        if len(selected_dev_paths) == 1:
            self.wipe_button.configure(state="normal")
            self.display_drive_details(selected_dev_paths[0])
        elif len(selected_dev_paths) > 1:
            self.wipe_button.configure(state="disabled") # Only allow one drive at a time for safety
            self.details_textbox.configure(state="normal")
            self.details_textbox.delete("1.0", "end")
            self.details_textbox.insert("1.0", "Please select only one drive to see details.")
            self.details_textbox.configure(state="disabled")
        else:
            self.wipe_button.configure(state="disabled")
            self.details_textbox.configure(state="normal")
            self.details_textbox.delete("1.0", "end")
            self.details_textbox.insert("1.0", "Select a drive to view its details.")
            self.details_textbox.configure(state="disabled")

    def display_drive_details(self, dev_path):
        dev_data = self.device_checkboxes[dev_path]["data"]
        details = (
            f"Device: {dev_path}\n"
            f"Model:  {dev_data.get('model') or 'N/A'}\n"
            f"Serial: {dev_data.get('serial') or 'N/A'}\n"
            f"Size:   {dev_data.get('size') or 'N/A'}\n"
            f"Type:   {dev_data.get('type') or 'N/A'}\n"
        )
        self.details_textbox.configure(state="normal")
        self.details_textbox.delete("1.0", "end")
        self.details_textbox.insert("1.0", details)
        self.details_textbox.configure(state="disabled")

    def confirm_wipe(self):
        selected_devices = [info["data"] for path, info in self.device_checkboxes.items() if info["var"].get()]
        self.controller.start_wipe_process(selected_devices)

# --- Confirmation Frame ---
class ConfirmationFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.main_label = customtkinter.CTkLabel(self, text="⚠️ FINAL CONFIRMATION ⚠️", font=("Roboto", 36, "bold"), text_color="orange")
        self.main_label.pack(pady=(100, 20))

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
        dev = devices[0] # We only handle one at a time
        info_text = (
            f"You are about to permanently destroy all data on:\n\n"
            f"Device: /dev/{dev.get('name')}\n"
            f"Model: {dev.get('model') or 'N/A'}\n"
            f"Size: {dev.get('size') or 'N/A'}"
        )
        self.info_label.configure(text=info_text)
        self.entry.delete(0, "end") # Clear entry box
        self.check_token(None) # Disable button

    def check_token(self, event):
        self.confirm_button.configure(state="normal" if self.entry.get() == "OBLITERATE" else "disabled")

# --- Wipe Progress Frame ---
class WipeProgressFrame(customtkinter.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.process = None
        self.start_time = 0

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
        
        self.finish_button = customtkinter.CTkButton(center_frame, text="Finished", command=lambda: controller.show_frame(MainFrame))

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def prepare_for_wipe(self, device_data):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        self.progress_bar.set(0)
        self.finish_button.pack_forget() # Hide finish button
        self.title_label.configure(text=f"Wiping /dev/{device_data['name']}")
        threading.Thread(target=self.run_wipe_script, args=(device_data,), daemon=True).start()

    def run_wipe_script(self, device_data):
        self.start_time = time.time()
        self.after(1000, self.update_timer)
        device_path = f"/dev/{device_data['name']}"
        command = ['bash', WIPE_SCRIPT_PATH, device_path, 'OBLITERATE']
        
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            
            # Threaded readers for stdout and stderr
            q_out, q_err = Queue(), Queue()
            threading.Thread(target=self.read_stream, args=(self.process.stdout, q_out), daemon=True).start()
            threading.Thread(target=self.read_stream, args=(self.process.stderr, q_err), daemon=True).start()
            
            # Check queues periodically
            self.after(100, self.check_queues, q_out, q_err)
            
        except Exception as e:
            self.log(f"CRITICAL FAILURE: {e}")

    def read_stream(self, stream, queue):
        for line in iter(stream.readline, ''):
            queue.put(line)

    def check_queues(self, q_out, q_err):
        # Handle stdout (for PROGRESS:)
        try:
            while True:
                line = q_out.get_nowait().strip()
                self.log(f"OUT: {line}")
                if line.startswith("PROGRESS:"):
                    self.update_progress_from_line(line)
                elif "STATUS:SUCCESS" in line:
                    self.wipe_finished(True)
        except Empty:
            pass

        # Handle stderr (for pv speed)
        try:
            while True:
                line = q_err.get_nowait().strip()
                # pv output is a carriage return, we just grab the last one
                if "MB/s" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if "MB/s" in part:
                            speed = parts[i-1] if i > 0 else "?"
                            self.speed_label.configure(text=f"Throughput: {speed} MB/s")
                            break
                else: # Log other errors
                    self.log(f"ERR: {line}")
        except Empty:
            pass
        
        # Keep checking if process is still running
        if self.process.poll() is None:
            self.after(100, self.check_queues, q_out, q_err)
        else: # Process finished
             if self.process.returncode != 0:
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
        else:
            self.progress_label.configure(text="Status: WIPE FAILED!", text_color="red")
            self.log("❌ WIPE FAILED. Check logs for errors.")
        self.finish_button.pack(pady=20)

    def update_timer(self):
        if self.process and self.process.poll() is None:
            elapsed = time.time() - self.start_time
            self.time_label.configure(text=f"Elapsed Time: {str(datetime.timedelta(seconds=int(elapsed)))}")
            self.after(1000, self.update_timer)

# --- Entry Point ---
if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: This application requires root privileges.")
        print("Please run with 'sudo python3 obliterator_gui.py'")
    else:
        app = App()
        app.mainloop()
