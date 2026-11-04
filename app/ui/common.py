# -*- coding: utf-8 -*-
"""Общие виджеты и диалоги для интерфейса портала."""

import tkinter as tk
from tkinter import ttk, messagebox

BG = "#f4f6fa"
CARD = "#ffffff"
ACCENT = "#2f5d9e"
ACCENT_DARK = "#244a7e"
DANGER = "#b23b3b"
OK = "#2e7d46"
MUTED = "#7a869a"

STATUS_COLORS = {
    "Работает": OK,
    "Уволен": DANGER,
    "На пенсии": "#8a5fb0",
}


def style_app(root):
    root.configure(bg=BG)
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    st.configure(".", font=("Segoe UI", 10), background=BG)
    st.configure("TFrame", background=BG)
    st.configure("Card.TFrame", background=CARD)
    st.configure("TLabel", background=BG, foreground="#222a35")
    st.configure("Card.TLabel", background=CARD, foreground="#222a35")
    st.configure("H1.TLabel", background=CARD, foreground=ACCENT,
                 font=("Segoe UI", 15, "bold"))
    st.configure("Muted.TLabel", background=CARD, foreground=MUTED)
    st.configure("Status.TLabel", background=BG, foreground=MUTED,
                 font=("Segoe UI", 9))
    st.configure("Treeview", rowheight=26, font=("Segoe UI", 10),
                 background=CARD, fieldbackground=CARD)
    st.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                 background="#e8edf5")
    st.map("Treeview", background=[("selected", ACCENT)],
           foreground=[("selected", "white")])
    st.configure("TButton", font=("Segoe UI", 10), padding=(10, 5))
    st.configure("Accent.TButton", background=ACCENT, foreground="white",
                 font=("Segoe UI", 10, "bold"), padding=(12, 6))
    st.map("Accent.TButton", background=[("active", ACCENT_DARK)])
    st.configure("Danger.TButton", background=DANGER, foreground="white")
    st.map("Danger.TButton", background=[("active", "#8f2f2f")])
    st.configure("TNotebook", background=BG, borderwidth=0)
    st.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(14, 6))
    st.map("TNotebook.Tab", background=[("selected", CARD)],
           expand=[("selected", (2, 2, 2, 0))])
    st.configure("TLabelframe", background=CARD)
    st.configure("TLabelframe.Label", background=CARD, foreground=ACCENT,
                 font=("Segoe UI", 10, "bold"))
    st.configure("Vertical.TScrollbar", background="#cfd8e6",
                 troughcolor=BG, arrowcolor=ACCENT)


class FormDialog(tk.Toplevel):
    """Модальное окно с формой из полей. Возвращает dict через self.result."""

    def __init__(self, parent, title, fields, width=460):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        self.entries = {}
        self.transient(parent)
        self.grab_set()
        frame = ttk.Frame(self, style="Card.TFrame", padding=14)
        frame.pack(fill="both", expand=True)
        for i, spec in enumerate(fields):
            kind = spec.get("kind", "entry")
            label = spec["label"]
            ttk.Label(frame, text=label + ":", style="Card.TLabel").grid(
                row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            if kind == "combo":
                var = tk.StringVar(value=spec.get("value", ""))
                cb = ttk.Combobox(frame, textvariable=var,
                                  values=spec.get("options", []),
                                  state=spec.get("state", "readonly"),
                                  width=28)
                cb.grid(row=i, column=1, sticky="we", pady=4)
                self.entries[spec["key"]] = var
            elif kind == "spin":
                var = tk.IntVar(value=int(spec.get("value", 0)))
                sp = ttk.Spinbox(frame, from_=spec.get("min", 0),
                                 to=spec.get("max", 9999999),
                                 textvariable=var, width=26)
                sp.grid(row=i, column=1, sticky="we", pady=4)
                self.entries[spec["key"]] = var
            else:
                e = ttk.Entry(frame, width=30)
                e.insert(0, str(spec.get("value", "")))
                e.grid(row=i, column=1, sticky="we", pady=4)
                if spec.get("focus", True):
                    e.focus_set()
                self.entries[spec["key"]] = e
        frame.columnconfigure(1, weight=1)
        btns = ttk.Frame(frame, style="Card.TFrame")
        btns.grid(row=len(fields), column=0, columnspan=2,
                  sticky="ew", pady=(14, 0))
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Сохранить", style="Accent.TButton",
                   command=self._ok).pack(side="right", padx=(0, 8))

    def _val(self, key):
        w = self.entries[key]
        return w.get().strip() if isinstance(w, (tk.StringVar, tk.IntVar)) \
            else w.get().strip()

    def values(self):
        return {k: self._val(k) for k in self.entries}

    def _ok(self):
        self.result = self.values()
        self.destroy()


def ask_form(parent, title, fields):
    dlg = FormDialog(parent, title, fields)
    parent.wait_window(dlg)
    return dlg.result


def center_dialog(dlg, parent, width=420, height=300):
    dlg.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    dlg.geometry(f"+{max(x,0)}+{max(y,0)}")


def info(parent, title, msg):
    messagebox.showinfo(title, msg, parent=parent)


def error(parent, title, msg):
    messagebox.showerror(title, msg, parent=parent)


def confirm(parent, title, msg):
    return messagebox.askyesno(title, msg, parent=parent)
