import os
import threading
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
import tkinter as tk
from tkcalendar import DateEntry

import pandas as pd
import numpy as np

from Data_Pull import ZabbixDataExporter


# =========================
# THEME
# =========================
ctk.set_appearance_mode("light")

PRIMARY = "#0067C0"
BG = "#F8F9FA"
TEXT = "#212121"
MUTED = "#666666"
BORDER = "#D0D7DE"
SUCCESS = "#388E3C"


# =========================
# HELPERS
# =========================
def find_parquet_file(root_folder: str):
    for dirpath, _, filenames in os.walk(root_folder):
        for f in filenames:
            if f.endswith(".parquet"):
                return os.path.join(dirpath, f)
    return None


# =========================
# APP
# =========================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Zabbix Export Tool")
        self.geometry("850x900")
        self.configure(fg_color=BG)

        self.current_parquet_path = None
        self.corr_btn = None

        self.container = ctk.CTkFrame(self, fg_color=BG)
        self.container.pack(fill="both", expand=True)

        self.build_ui()

    # =========================
    def build_ui(self):
        self.form_frame = ctk.CTkScrollableFrame(self.container, fg_color=BG)
        self.form_frame.pack(fill="both", expand=True)

        self.loading_frame = ctk.CTkFrame(self.container, fg_color=BG)

        self.build_form()
        self.build_loading()

    # =========================
    def section(self, text):
        ctk.CTkLabel(
            self.form_frame,
            text=text,
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT
        ).pack(anchor="w", pady=(20, 5))

        ctk.CTkFrame(self.form_frame, height=1, fg_color="#E5E7EB").pack(fill="x")

    # =========================
    def field(self, label, show=None):
        wrapper = ctk.CTkFrame(self.form_frame, fg_color=BG)
        wrapper.pack(fill="x", pady=6)

        ctk.CTkLabel(wrapper, text=label, text_color=MUTED).pack(anchor="w")

        entry = ctk.CTkEntry(
            wrapper,
            height=40,
            show=show,
            fg_color="white",
            border_color=BORDER
        )
        entry.pack(fill="x")

        return entry

    # =========================
    def date_field(self, parent, label):
        wrapper = ctk.CTkFrame(parent, fg_color=BG)
        wrapper.pack(fill="x", pady=6)

        ctk.CTkLabel(wrapper, text=label, text_color=MUTED).pack(anchor="w")

        container = ctk.CTkFrame(wrapper, fg_color="white")
        container.pack(fill="x")

        date_picker = DateEntry(container, date_pattern="dd/mm/yyyy")
        date_picker.pack(fill="x", padx=5, pady=5)

        return date_picker

    # =========================
    def time_field(self, parent, label):
        wrapper = ctk.CTkFrame(parent, fg_color=BG)
        wrapper.pack(fill="x", pady=6)

        ctk.CTkLabel(wrapper, text=label, text_color=MUTED).pack(anchor="w")

        row = ctk.CTkFrame(wrapper, fg_color=BG)
        row.pack(fill="x")

        hour = ctk.CTkOptionMenu(row, values=[f"{i:02d}" for i in range(24)], width=120)
        hour.set("00")
        hour.pack(side="left", padx=5)

        minute = ctk.CTkOptionMenu(row, values=[f"{i:02d}" for i in range(60)], width=120)
        minute.set("00")
        minute.pack(side="left")

        return hour, minute

    # =========================
    def build_form(self):

        ctk.CTkLabel(
            self.form_frame,
            text="Zabbix Export Setup",
            font=("Segoe UI", 20, "bold"),
            text_color=TEXT
        ).pack(anchor="w", pady=10)

        self.section("API")
        self.url = self.field("Zabbix URL")
        self.token = self.field("API Token", show="*")

        self.section("Database")
        self.db_host = self.field("Host")
        self.db_port = self.field("Port")
        self.db_name = self.field("Database Name")
        self.db_user = self.field("User")
        self.db_pass = self.field("Password", show="*")

        self.section("Time Range")
        self.start_date = self.date_field(self.form_frame, "Start Date")
        self.start_hour, self.start_minute = self.time_field(self.form_frame, "Start Time")

        self.end_date = self.date_field(self.form_frame, "End Date")
        self.end_hour, self.end_minute = self.time_field(self.form_frame, "End Time")

        self.section("Output Folder")

        out = ctk.CTkFrame(self.form_frame, fg_color=BG)
        out.pack(fill="x")

        self.output = tk.StringVar(value="output_data")

        ctk.CTkEntry(out, textvariable=self.output, height=40).pack(
            side="left", fill="x", expand=True
        )

        ctk.CTkButton(out, text="Browse", command=self.browse).pack(side="left", padx=10)

        # ONLY export button initially
        self.bottom = ctk.CTkFrame(self.container, fg_color=BG)
        self.bottom.pack(fill="x", side="bottom")

        self.btn = ctk.CTkButton(
            self.bottom,
            text="Continue",
            fg_color=PRIMARY,
            height=45,
            command=self.start
        )
        self.btn.pack(fill="x", padx=20, pady=10)

    # =========================
    def build_loading(self):
        ctk.CTkLabel(
            self.loading_frame,
            text="Processing...",
            font=("Segoe UI", 18, "bold"),
            text_color=TEXT
        ).pack(pady=20)

        self.progress = ctk.CTkProgressBar(self.loading_frame, width=400)
        self.progress.pack(pady=20)
        self.progress.set(0)

        self.status = ctk.CTkLabel(self.loading_frame, text="")
        self.status.pack()

        self.done = ctk.CTkLabel(self.loading_frame, text="", text_color=SUCCESS)
        self.done.pack(pady=10)

    # =========================
    def browse(self):
        path = filedialog.askdirectory()
        if path:
            self.output.set(path)

    # =========================
    def to_epoch(self, date_obj, hour, minute):
        dt = datetime.strptime(
            f"{date_obj.get_date().strftime('%d/%m/%Y')} {hour}:{minute}",
            "%d/%m/%Y %H:%M"
        )
        return int(dt.timestamp())

    # =========================
    def start(self):
        self.btn.configure(state="disabled")

        # hide continue button permanently
        self.btn.pack_forget()

        self.form_frame.pack_forget()
        self.loading_frame.pack(fill="both", expand=True)

        self.progress.set(0)
        self.status.configure(text="Starting...")

        threading.Thread(target=self.run, daemon=True).start()

    # =========================
    def run(self):
        try:
            api_config = {"url": self.url.get().strip()}

            db_config = {
                "host": self.db_host.get().strip(),
                "port": self.db_port.get().strip(),
                "dbname": self.db_name.get().strip(),
                "user": self.db_user.get().strip(),
                "password": self.db_pass.get()
            }

            start_time = self.to_epoch(self.start_date, self.start_hour.get(), self.start_minute.get())
            end_time = self.to_epoch(self.end_date, self.end_hour.get(), self.end_minute.get())

            output_folder = self.output.get().strip()

            if not output_folder:
                raise ValueError("Output folder is required")

            os.makedirs(output_folder, exist_ok=True)

            def log(msg):
                self.after(0, lambda: self.status.configure(text=msg))

            def progress(current, total):
                self.after(0, lambda: self.progress.set(current / total if total else 0))

            exporter = ZabbixDataExporter(
                api_config=api_config,
                db_config=db_config,
                api_token=self.token.get().strip(),
                start_time=start_time,
                end_time=end_time,
                output_folder=output_folder,
                logger=log,
                progress_callback=progress
            )

            exporter.export_all_hosts()

            parquet_path = find_parquet_file(output_folder)

            if not parquet_path:
                raise FileNotFoundError("No parquet file found in output directory")

            self.current_parquet_path = parquet_path

            self.after(0, self.finish)

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, self.reset_ui)

    # =========================
    def finish(self):
        self.progress.set(1)
        self.status.configure(text="Export completed successfully.")
        self.done.configure(text="✓ Export Done")

        # create correlation button ONLY here
        if self.corr_btn is None:
            self.corr_btn = ctk.CTkButton(
                self.bottom,
                text="Run Correlation",
                fg_color="#444",
                height=45,
                command=self.start_correlation
            )
            self.corr_btn.pack(fill="x", padx=20, pady=(0, 10))
        else:
            self.corr_btn.pack(fill="x", padx=20, pady=(0, 10))

    # =========================
    def reset_ui(self):
        self.loading_frame.pack_forget()
        self.form_frame.pack(fill="both", expand=True)

    # =========================
    def start_correlation(self):

        if not self.current_parquet_path or not os.path.exists(self.current_parquet_path):
            messagebox.showerror("Error", "Parquet file not found.")
            return

        self.corr_btn.configure(state="disabled")

        self.status.configure(text="Running correlation...")

        threading.Thread(target=self.run_correlation, daemon=True).start()

    # =========================
    def run_correlation(self):

        try:
            output_folder = os.path.dirname(self.current_parquet_path)

            df = pd.read_parquet(self.current_parquet_path)

            df["clock"] = pd.to_datetime(df["clock"], unit="s")

            df_wide = df.pivot_table(
                index="clock",
                columns="name",
                values="value",
                aggfunc="mean"
            )

            df_wide = df_wide.resample("3min").mean().ffill().fillna(0)

            clean = df_wide.loc[:, df_wide.nunique() > 1]
            corr = clean.corr(method="pearson")

            corr.index.name = None
            corr.columns.name = None

            mask = np.triu(np.ones(corr.shape, dtype=bool), k=1)

            pairs = corr.where(mask).stack().reset_index()
            pairs.columns = ["First Item", "Second Item", "Corr Value"]
            pairs = pairs.dropna(subset=["Corr Value"])

            pairs = pairs.sort_values(
                by="Corr Value",
                key=lambda x: x.abs(),
                ascending=False
            )

            out_file = os.path.join(output_folder, "correlation_analysis.xlsx")

            with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
                pairs.to_excel(writer, sheet_name="Cross Correlation", index=False)

            os.remove(self.current_parquet_path)

            self.after(0, lambda: self.status.configure(text="Correlation completed"))
            self.after(0, lambda: self.done.configure(text="✓ Correlation Done"))
            self.after(0, lambda: messagebox.showinfo("Done", f"Saved:\n{out_file}"))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

        finally:
            self.after(0, lambda: self.corr_btn.configure(state="normal"))


# =========================
if __name__ == "__main__":
    App().mainloop()