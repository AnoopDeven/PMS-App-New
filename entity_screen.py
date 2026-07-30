import os
import json
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import date
from database import (initialize_db, ensure_financial_year, set_meta, get_meta,
                      get_financial_years, create_financial_year, carry_forward_fy,
                      set_active_fy)

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pms_settings.json")


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"data_folder": ""}


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def scan_entities_in_folder(folder):
    entities = []
    if not os.path.isdir(folder):
        return entities
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".db"):
            db_path = os.path.join(folder, fname)
            name = fname[:-3].replace("_", " ")
            entities.append({"name": name, "db_path": db_path})
    return entities


class EntityScreen(ctk.CTkFrame):
    def __init__(self, master, on_select_entity):
        super().__init__(master, fg_color="#F0F4FF")
        self.pack(fill="both", expand=True)
        self.on_select_entity = on_select_entity
        self.settings = load_settings()
        self._build_ui()

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        header = ctk.CTkFrame(self, fg_color="#1B2B6B", corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="Payment Management System",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="white").pack(pady=20)

        folder_card = ctk.CTkFrame(self, fg_color="white", corner_radius=12)
        folder_card.pack(fill="x", padx=60, pady=(20, 8))
        fi = ctk.CTkFrame(folder_card, fg_color="transparent")
        fi.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(fi, text="Data Folder:",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#1B2B6B").pack(side="left", padx=(0, 10))
        folder = self.settings.get("data_folder", "")
        ctk.CTkLabel(fi, text=folder or "No folder selected",
                     font=ctk.CTkFont(size=12), text_color="#555").pack(side="left", expand=True, anchor="w")
        ctk.CTkButton(fi, text="Change Folder", width=130,
                      fg_color="#1B4FD8", hover_color="#1440B0",
                      command=self._browse_folder).pack(side="right")

        if not folder or not os.path.isdir(folder):
            ctk.CTkLabel(self,
                         text="Select a data folder above to view or create entities.",
                         font=ctk.CTkFont(size=14), text_color="#666").pack(pady=40)
            return

        entities = scan_entities_in_folder(folder)

        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(fill="x", padx=60, pady=(4, 8))
        ctk.CTkButton(action_row, text="+ Create Entity", width=150,
                      fg_color="#1B4FD8", hover_color="#1440B0",
                      command=self._open_create).pack(side="left")

        if not entities:
            ctk.CTkLabel(self,
                         text="No entities found.\nClick 'Create Entity' to start.",
                         font=ctk.CTkFont(size=14), text_color="#666").pack(pady=40)
            return

        ctk.CTkLabel(self, text="Select an Entity",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w", padx=60, pady=(4, 4))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=60, pady=(0, 24))
        for entity in entities:
            self._make_entity_row(scroll, entity)

    def _make_entity_row(self, parent, entity):
        card = ctk.CTkFrame(parent, fg_color="white", corner_radius=10,
                             border_width=1, border_color="#D0D8FF")
        card.pack(fill="x", pady=5)
        card.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=0, sticky="w", padx=16, pady=12)
        ctk.CTkLabel(info, text=entity["name"],
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#1B2B6B").pack(anchor="w")
        ctk.CTkLabel(info, text=entity["db_path"],
                     font=ctk.CTkFont(size=11), text_color="#888").pack(anchor="w")

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=0, column=1, padx=12, pady=12)
        ctk.CTkButton(btns, text="Select", width=90,
                      fg_color="#16A34A", hover_color="#15803D",
                      command=lambda e=entity: self._select(e)).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Alter", width=70,
                      fg_color="#6366F1", hover_color="#4F46E5",
                      command=lambda e=entity: self._open_alter(e)).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="New FY", width=80,
                      fg_color="#D97706", hover_color="#B45309",
                      command=lambda e=entity: self._open_new_fy(e)).pack(side="left", padx=4)

    def _browse_folder(self):
        path = filedialog.askdirectory(title="Select Data Folder")
        if path:
            self.settings["data_folder"] = path
            save_settings(self.settings)
            self._build_ui()

    def _select(self, entity):
        db_path = entity["db_path"]
        if not os.path.exists(db_path):
            messagebox.showerror("Error", f"Database not found:\n{db_path}")
            return
        initialize_db(db_path)
        fy_type = get_meta(db_path, "fy_type", "april_march")
        ensure_financial_year(db_path, fy_type)
        self.on_select_entity(entity["name"], db_path)

    def _open_create(self):
        folder = self.settings.get("data_folder", "")
        CreateEntityDialog(self.winfo_toplevel(), data_folder=folder,
                           on_save=self._after_action)

    def _open_alter(self, entity):
        AlterEntityDialog(self.winfo_toplevel(), entity=entity)

    def _open_new_fy(self, entity):
        db_path = entity["db_path"]
        if not os.path.exists(db_path):
            messagebox.showerror("Error", "Entity database not found.")
            return
        initialize_db(db_path)
        NewFYDialog(self.winfo_toplevel(), db_path=db_path, on_save=self._after_action)

    def _after_action(self):
        self._build_ui()


class CreateEntityDialog(ctk.CTkToplevel):
    def __init__(self, master, data_folder, on_save):
        super().__init__(master)
        self.title("Create Entity")
        self.geometry("460x360")
        self.resizable(False, False)
        self.grab_set()
        self.data_folder = data_folder
        self.on_save = on_save
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        pad = {"padx": 20, "pady": 8}

        ctk.CTkLabel(self, text="Entity Name *",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", **pad)
        self._name = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self._name).grid(row=0, column=1, sticky="ew", **pad)

        ctk.CTkLabel(self, text="Financial Year *",
                     font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", **pad)
        self._fy_type = tk.StringVar(value="april_march")
        ctk.CTkOptionMenu(self, values=["april_march", "calendar_year"],
                          variable=self._fy_type).grid(row=1, column=1, sticky="w", **pad)

        ctk.CTkLabel(self, text="FY Start Date *",
                     font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", **pad)
        self._fy_start = tk.StringVar(value="2024-04-01")
        ctk.CTkEntry(self, textvariable=self._fy_start,
                     placeholder_text="YYYY-MM-DD").grid(row=2, column=1, sticky="ew", **pad)

        ctk.CTkLabel(self, text="Phone").grid(row=3, column=0, sticky="w", **pad)
        self._phone = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self._phone).grid(row=3, column=1, sticky="ew", **pad)

        ctk.CTkLabel(self, text="Email").grid(row=4, column=0, sticky="w", **pad)
        self._email = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self._email).grid(row=4, column=1, sticky="ew", **pad)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=5, column=0, columnspan=2, pady=20)
        ctk.CTkButton(btns, text="Cancel", fg_color="#6B7280",
                      command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Create", fg_color="#1B4FD8",
                      command=self._create).pack(side="left", padx=8)

    def _create(self):
        name = self._name.get().strip()
        if not name:
            messagebox.showerror("Error", "Entity name is required.", parent=self)
            return
        fy_start = self._fy_start.get().strip()
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
        db_path = os.path.join(self.data_folder, f"{safe}.db")
        if os.path.exists(db_path):
            messagebox.showerror("Error", f"Entity '{name}' already exists.", parent=self)
            return
        fy_type = self._fy_type.get()
        try:
            start = date.fromisoformat(fy_start)
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.", parent=self)
            return
        if fy_type == "april_march":
            end = date(start.year + 1, 3, 31)
            label = f"FY {start.year}-{str(start.year + 1)[2:]}"
        else:
            end = date(start.year, 12, 31)
            label = f"FY {start.year}"
        initialize_db(db_path)
        set_meta(db_path, "entity_name", name)
        set_meta(db_path, "fy_type", fy_type)
        set_meta(db_path, "phone", self._phone.get().strip())
        set_meta(db_path, "email", self._email.get().strip())
        create_financial_year(db_path, label, str(start), str(end), fy_type)
        messagebox.showinfo("Created", f"Entity '{name}' created!", parent=self)
        self.on_save()
        self.destroy()


class AlterEntityDialog(ctk.CTkToplevel):
    def __init__(self, master, entity):
        super().__init__(master)
        self.title("Alter Entity")
        self.geometry("440x260")
        self.resizable(False, False)
        self.grab_set()
        self.entity = entity
        self._build()

    def _build(self):
        db_path = self.entity["db_path"]
        self.grid_columnconfigure(1, weight=1)
        pad = {"padx": 20, "pady": 8}
        ctk.CTkLabel(self, text="Entity Name",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", **pad)
        ctk.CTkLabel(self, text=self.entity["name"],
                     text_color="#1B4FD8").grid(row=0, column=1, sticky="w", **pad)
        ctk.CTkLabel(self, text="Phone").grid(row=1, column=0, sticky="w", **pad)
        self._phone = tk.StringVar(value=get_meta(db_path, "phone", ""))
        ctk.CTkEntry(self, textvariable=self._phone).grid(row=1, column=1, sticky="ew", **pad)
        ctk.CTkLabel(self, text="Email").grid(row=2, column=0, sticky="w", **pad)
        self._email = tk.StringVar(value=get_meta(db_path, "email", ""))
        ctk.CTkEntry(self, textvariable=self._email).grid(row=2, column=1, sticky="ew", **pad)
        ctk.CTkLabel(self, text="DB Path").grid(row=3, column=0, sticky="w", **pad)
        ctk.CTkLabel(self, text=db_path, font=ctk.CTkFont(size=10),
                     text_color="#888", wraplength=280).grid(row=3, column=1, sticky="w", **pad)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=4, column=0, columnspan=2, pady=20)
        ctk.CTkButton(btns, text="Cancel", fg_color="#6B7280",
                      command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Save", fg_color="#1B4FD8",
                      command=self._save).pack(side="left", padx=8)

    def _save(self):
        db_path = self.entity["db_path"]
        set_meta(db_path, "phone", self._phone.get().strip())
        set_meta(db_path, "email", self._email.get().strip())
        messagebox.showinfo("Saved", "Entity updated.", parent=self)
        self.destroy()


class NewFYDialog(ctk.CTkToplevel):
    """Create a new Financial Year with carry-forward of closing balances."""
    def __init__(self, master, db_path, on_save):
        super().__init__(master)
        self.title("Create New Financial Year")
        self.geometry("480x360")
        self.resizable(False, False)
        self.grab_set()
        self.db_path = db_path
        self.on_save = on_save
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        pad = {"padx": 20, "pady": 10}

        fy_type = get_meta(self.db_path, "fy_type", "april_march")
        fys = get_financial_years(self.db_path)

        info_text = f"Current FY type: {fy_type}\n"
        if fys:
            last_fy = fys[0]
            info_text += f"Last FY: {last_fy['label']} (ends {last_fy['end_date']})"
        ctk.CTkLabel(self, text=info_text,
                     font=ctk.CTkFont(size=12), text_color="#555",
                     justify="left").grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 4), sticky="w")

        ctk.CTkLabel(self, text="New FY Label *",
                     font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", **pad)
        self._label = tk.StringVar()
        if fys:
            last = fys[0]
            if fy_type == "april_march":
                parts = last["end_date"].split("-")
                next_start_year = int(parts[0]) + 1
                self._label.set(f"FY {next_start_year}-{str(next_start_year + 1)[2:]}")
            else:
                next_year = int(last["end_date"][:4]) + 1
                self._label.set(f"FY {next_year}")
        ctk.CTkEntry(self, textvariable=self._label).grid(row=1, column=1, sticky="ew", **pad)

        ctk.CTkLabel(self, text="Start Date *",
                     font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", **pad)
        self._start = tk.StringVar()
        if fys:
            last = fys[0]
            end_parts = last["end_date"].split("-")
            if fy_type == "april_march":
                self._start.set(f"{int(end_parts[0]) + 1}-04-01")
            else:
                self._start.set(f"{int(end_parts[0]) + 1}-01-01")
        ctk.CTkEntry(self, textvariable=self._start,
                     placeholder_text="YYYY-MM-DD").grid(row=2, column=1, sticky="ew", **pad)

        ctk.CTkLabel(self, text="End Date *",
                     font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, sticky="w", **pad)
        self._end = tk.StringVar()
        if fys:
            last = fys[0]
            end_parts = last["end_date"].split("-")
            if fy_type == "april_march":
                self._end.set(f"{int(end_parts[0]) + 2}-03-31")
            else:
                self._end.set(f"{int(end_parts[0]) + 1}-12-31")
        ctk.CTkEntry(self, textvariable=self._end,
                     placeholder_text="YYYY-MM-DD").grid(row=3, column=1, sticky="ew", **pad)

        self._carry_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(self, text="Carry forward vendor closing balances",
                        variable=self._carry_var).grid(row=4, column=0, columnspan=2, padx=20, pady=8, sticky="w")

        note = ctk.CTkLabel(self,
                             text="Carry forward: Vendor payable balance → new opening balance\n"
                                  "Cash/Bank accounts are NOT carried forward.",
                             font=ctk.CTkFont(size=10), text_color="#888")
        note.grid(row=5, column=0, columnspan=2, padx=20, sticky="w")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=6, column=0, columnspan=2, pady=20)
        ctk.CTkButton(btns, text="Cancel", fg_color="#6B7280",
                      command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Create New FY", fg_color="#D97706", hover_color="#B45309",
                      command=self._create).pack(side="left", padx=8)

    def _create(self):
        label = self._label.get().strip()
        start = self._start.get().strip()
        end = self._end.get().strip()
        fy_type = get_meta(self.db_path, "fy_type", "april_march")
        if not label or not start or not end:
            messagebox.showerror("Error", "All fields are required.", parent=self)
            return
        try:
            date.fromisoformat(start)
            date.fromisoformat(end)
        except ValueError:
            messagebox.showerror("Error", "Use YYYY-MM-DD date format.", parent=self)
            return

        if self._carry_var.get():
            new_fy_id = carry_forward_fy(self.db_path, label, start, end, fy_type)
        else:
            new_fy_id = create_financial_year(self.db_path, label, start, end, fy_type)
            set_active_fy(self.db_path, new_fy_id)

        messagebox.showinfo("Created",
                            f"New FY '{label}' created successfully!\n"
                            f"{'Balances carried forward.' if self._carry_var.get() else ''}",
                            parent=self)
        self.on_save()
        self.destroy()
