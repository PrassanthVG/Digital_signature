"""
Simple Tkinter UI to sign PDFs with JSignPdf using a smart-card certificate.
Select a PDF, adjust options if needed, and click Sign PDF.
"""
from __future__ import annotations

import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk


DEFAULT_OWNER_PASSWORD = "Owner#Strong#987"
DEFAULT_CERT_ALIAS = "NAME OF THE CERT."
DEFAULT_OUTPUT_SUFFIX = "_signed"
DEFAULT_JAVA_CANDIDATES = [
    r"C:\tools\temurin-jre\jdk-17.0.17+10-jre\bin\java.exe",
    r"C:\Program Files\Java\jre-17\bin\java.exe",
    r"C:\Program Files\Java\jre1.8.0_371\bin\java.exe",
    "java",
]
DEFAULT_JSIGN_PATH = r"C:\tools\JSignPdf\JSignPdf.jar"
DEFAULT_PRINTING = "Allow printing"
CERT_QUERY_COMMAND = (
    "Get-ChildItem Cert:\\CurrentUser\\My | "
    "Where-Object { $_.HasPrivateKey } | "
    "Select-Object -ExpandProperty Subject"
)
DEFAULT_SIG_PAGE = "1"
DEFAULT_SIG_POSITION = "Bottom right"
DEFAULT_SIG_IMAGE = r"C:\tools\img\adobe_style.png"
SIG_WIDTH = 240
SIG_HEIGHT = 90
SIG_MARGIN_X = 36
SIG_MARGIN_Y = 36

PERMISSION_LABELS = [
    ("Allow commenting", "allow_commenting", True),
    ("Allow content copying", "allow_copying", False),
    ("Allow content copying for accessibility", "allow_accessibility_copy", True),
    ("Allow editing file content", "allow_editing", False),
    ("Allow filling form fields", "allow_form_fill", False),
    ("Allow signing (additional signatures)", "allow_signing", False),
]


def extract_common_name(subject: str) -> str:
    match = re.search(r"CN=([^,]+)", subject, flags=re.IGNORECASE)
    return match.group(1).strip() if match else subject.strip()


def list_cert_aliases() -> list[str]:
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", CERT_QUERY_COMMAND],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []

    subjects = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    aliases: list[str] = []
    seen: set[str] = set()
    for subject in subjects:
        alias = extract_common_name(subject)
        if alias not in seen:
            seen.add(alias)
            aliases.append(alias)
    return aliases


def build_signature_text(alias: str) -> str:
    signer = alias or "Certified signer"
    now = datetime.now().astimezone()
    date_line = now.strftime("%Y.%m.%d")
    tz_raw = now.strftime("%z")
    if len(tz_raw) == 5:
        tz_fmt = f"{tz_raw[:3]}'{tz_raw[3:]}'"
    else:
        tz_fmt = tz_raw
    time_line = now.strftime("%H:%M:%S ") + tz_fmt
    lines = [
        "Digitally signed",
        f"by {signer}",
        f"Date: {date_line}",
        time_line,
    ]
    return "\n".join(lines)


def find_default_java() -> str:
    for candidate in DEFAULT_JAVA_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return "java"


class SignerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("img SIGN")

        # paths frame
        paths_frame = tk.LabelFrame(root, text="Paths")
        paths_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

        tk.Label(paths_frame, text="PDF file:").grid(row=0, column=0, sticky="w", pady=2)
        self.pdf_var = tk.StringVar()
        pdf_entry = tk.Entry(paths_frame, textvariable=self.pdf_var, width=60)
        pdf_entry.grid(row=0, column=1, sticky="we", pady=2)
        tk.Button(paths_frame, text="Browse…", command=self.select_pdf).grid(row=0, column=2, padx=4, pady=2)

        tk.Label(paths_frame, text="Java executable:").grid(row=1, column=0, sticky="w", pady=2)
        self.java_var = tk.StringVar(value=find_default_java())
        java_entry = tk.Entry(paths_frame, textvariable=self.java_var, width=60)
        java_entry.grid(row=1, column=1, sticky="we", pady=2)
        tk.Button(paths_frame, text="Browse…", command=self.select_java).grid(row=1, column=2, padx=4, pady=2)

        tk.Label(paths_frame, text="JSignPdf.jar:").grid(row=2, column=0, sticky="w", pady=2)
        self.jsign_var = tk.StringVar(value=DEFAULT_JSIGN_PATH)
        jsign_entry = tk.Entry(paths_frame, textvariable=self.jsign_var, width=60)
        jsign_entry.grid(row=2, column=1, sticky="we", pady=2)
        tk.Button(paths_frame, text="Browse…", command=self.select_jsign).grid(row=2, column=2, padx=4, pady=2)

        paths_frame.columnconfigure(1, weight=1)

        # options frame
        opts_frame = tk.LabelFrame(root, text="Signing options")
        opts_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        tk.Label(opts_frame, text="Certificate:").grid(row=0, column=0, sticky="w", pady=2)
        self.alias_var = tk.StringVar()
        self.alias_combo = ttk.Combobox(opts_frame, textvariable=self.alias_var, width=40)
        self.alias_combo.grid(row=0, column=1, sticky="we", pady=2)
        tk.Button(opts_frame, text="Refresh", command=self.refresh_cert_list).grid(row=0, column=2, padx=4, pady=2)

        tk.Label(opts_frame, text="Owner password:").grid(row=1, column=0, sticky="w", pady=2)
        self.owner_pwd_var = tk.StringVar(value=DEFAULT_OWNER_PASSWORD)
        tk.Entry(opts_frame, textvariable=self.owner_pwd_var, width=40, show="*").grid(row=1, column=1, sticky="we", pady=2)

        tk.Label(opts_frame, text="User password (optional):").grid(row=2, column=0, sticky="w", pady=2)
        self.user_pwd_var = tk.StringVar()
        tk.Entry(opts_frame, textvariable=self.user_pwd_var, width=40, show="*").grid(row=2, column=1, sticky="we", pady=2)

        tk.Label(opts_frame, text="TSA URL (optional):").grid(row=3, column=0, sticky="w", pady=2)
        self.tsa_var = tk.StringVar()
        tk.Entry(opts_frame, textvariable=self.tsa_var, width=40).grid(row=3, column=1, sticky="we", pady=2)

        tk.Label(opts_frame, text="Output suffix:").grid(row=4, column=0, sticky="w", pady=2)
        self.output_suffix_var = tk.StringVar(value=DEFAULT_OUTPUT_SUFFIX)
        tk.Entry(opts_frame, textvariable=self.output_suffix_var, width=40).grid(row=4, column=1, sticky="we", pady=2)

        tk.Label(opts_frame, text="Visible signature page:").grid(row=5, column=0, sticky="w", pady=2)
        self.page_var = tk.StringVar(value=DEFAULT_SIG_PAGE)
        tk.Spinbox(opts_frame, from_=1, to=9999, textvariable=self.page_var, width=6).grid(
            row=5, column=1, sticky="w", pady=2
        )

        tk.Label(opts_frame, text="Visible placement:").grid(row=6, column=0, sticky="w", pady=2)
        self.position_var = tk.StringVar(value=DEFAULT_SIG_POSITION)
        tk.OptionMenu(opts_frame, self.position_var, "Bottom left", "Bottom right").grid(
            row=6, column=1, sticky="w", pady=2
        )

        tk.Label(opts_frame, text="Signature PNG:").grid(row=7, column=0, sticky="w", pady=2)
        self.image_var = tk.StringVar(value=DEFAULT_SIG_IMAGE)
        tk.Entry(opts_frame, textvariable=self.image_var, width=40).grid(row=7, column=1, sticky="we", pady=2)
        tk.Button(opts_frame, text="Browse…", command=self.select_image).grid(row=7, column=2, padx=4, pady=2)

        opts_frame.columnconfigure(1, weight=1)

        # permissions frame
        perm_frame = tk.LabelFrame(root, text="PDF permissions")
        perm_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        self.perm_vars: dict[str, tk.BooleanVar] = {}
        for idx, (label, key, default) in enumerate(PERMISSION_LABELS):
            var = tk.BooleanVar(value=default)
            self.perm_vars[key] = var
            tk.Checkbutton(perm_frame, text=label, variable=var).grid(
                row=idx, column=0, sticky="w", pady=1
            )

        tk.Label(perm_frame, text="Printing:").grid(
            row=len(PERMISSION_LABELS), column=0, sticky="w", pady=(6, 1)
        )
        self.printing_var = tk.StringVar(value=DEFAULT_PRINTING)
        printing_options = ["Allow printing", "Allow degraded printing", "Disallow printing"]
        tk.OptionMenu(perm_frame, self.printing_var, *printing_options).grid(
            row=len(PERMISSION_LABELS) + 1, column=0, sticky="w"
        )

        # action frame
        action_frame = tk.Frame(root)
        action_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
        action_frame.columnconfigure(0, weight=1)

        self.sign_button = tk.Button(action_frame, text="Sign PDF", command=self.sign_pdf, state=tk.NORMAL)
        self.sign_button.grid(row=0, column=0, sticky="e")

        # log frame
        log_frame = tk.LabelFrame(root, text="Log")
        log_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
        self.log_widget = scrolledtext.ScrolledText(log_frame, height=10, width=80, state=tk.DISABLED)
        self.log_widget.pack(fill="both", expand=True)

        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)
        self.refresh_cert_list(initial=True)

    def log(self, message: str) -> None:
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state=tk.DISABLED)

    def select_pdf(self) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.pdf_var.set(file_path)

    def select_java(self) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("Java executable", "java.exe"), ("All files", "*.*")])
        if file_path:
            self.java_var.set(file_path)

    def select_jsign(self) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("JAR files", "*.jar"), ("All files", "*.*")])
        if file_path:
            self.jsign_var.set(file_path)

    def select_image(self) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if file_path:
            self.image_var.set(file_path)

    def sign_pdf(self) -> None:
        pdf_path = Path(self.pdf_var.get()).expanduser()
        java_path = Path(self.java_var.get()).expanduser()
        jsign_path = Path(self.jsign_var.get()).expanduser()

        if not pdf_path.exists():
            messagebox.showerror("Missing file", "Please select a valid PDF file.")
            return
        if not java_path.exists() and java_path.name.lower() != "java":
            messagebox.showerror("Missing Java", "Java executable not found. Adjust the path and try again.")
            return
        if not jsign_path.exists():
            messagebox.showerror("Missing JSignPdf", "JSignPdf.jar not found. Adjust the path and try again.")
            return

        self.sign_button.configure(state=tk.DISABLED)
        self.log("Starting signing job…")

        thread = threading.Thread(
            target=self._run_signer,
            kwargs=dict(pdf_path=pdf_path, java_path=java_path, jsign_path=jsign_path),
            daemon=True,
        )
        thread.start()

    def _run_signer(self, pdf_path: Path, java_path: Path, jsign_path: Path) -> None:
        output_dir = pdf_path.parent
        suffix = self.output_suffix_var.get().strip() or DEFAULT_OUTPUT_SUFFIX

        allow_signing = self.perm_vars["allow_signing"].get()
        cert_level = (
            "CERTIFIED_FORM_FILLING_AND_ANNOTATIONS" if allow_signing else "CERTIFIED_NO_CHANGES_ALLOWED"
        )

        command = [
            str(java_path),
            "-jar",
            str(jsign_path),
            "-kst",
            "WINDOWS-MY",
            "-cl",
            cert_level,
            "-pe",
            "PASSWORD",
            "-opwd",
            self.owner_pwd_var.get(),
            "-os",
            suffix,
            "-d",
            str(output_dir),
        ]

        cert_alias = self.alias_var.get().strip()
        if cert_alias:
            command.extend(["-ka", cert_alias])

        signature_name = cert_alias or "Certified signer"
        command.extend(["-sn", signature_name, "--l2-text", build_signature_text(signature_name)])

        # visible signature placement
        page_value = self.page_var.get().strip()
        try:
            page_num = max(1, int(page_value))
        except ValueError:
            page_num = 1

        placement = self.position_var.get()
        if placement not in {"Bottom left", "Bottom right"}:
            placement = "Bottom right"

        if placement == "Bottom left":
            llx = SIG_MARGIN_X
            lly = SIG_MARGIN_Y
            urx = SIG_MARGIN_X + SIG_WIDTH
            ury = SIG_MARGIN_Y + SIG_HEIGHT
        else:
            llx = -(SIG_MARGIN_X + SIG_WIDTH)
            lly = SIG_MARGIN_Y
            urx = -SIG_MARGIN_X
            ury = SIG_MARGIN_Y + SIG_HEIGHT

        command.extend(
            [
                "-V",
                "-pg",
                str(page_num),
                "-llx",
                str(llx),
                "-lly",
                str(lly),
                "-urx",
                str(urx),
                "-ury",
                str(ury),
                "-fs",
                "10",
            ]
        )

        image_path = Path(self.image_var.get()).expanduser()
        if image_path.exists():
            command.extend(["--img-path", str(image_path), "--render-mode", "GRAPHIC_AND_DESCRIPTION"])
        else:
            self._log_from_thread("Signature PNG not found; continuing without background image.")

        if not self.perm_vars["allow_commenting"].get():
            command.append("--disable-modify-annotations")
        if not self.perm_vars["allow_copying"].get():
            command.append("--disable-copy")
        if not self.perm_vars["allow_accessibility_copy"].get():
            command.append("--disable-screen-readers")
        if not self.perm_vars["allow_editing"].get():
            command.append("--disable-modify-content")
        if not self.perm_vars["allow_form_fill"].get():
            command.append("--disable-fill")

        printing_map = {
            "Allow printing": "ALLOW_PRINTING",
            "Allow degraded printing": "ALLOW_DEGRADED_PRINTING",
            "Disallow printing": "DISALLOW_PRINTING",
        }
        command.extend(["-pr", printing_map.get(self.printing_var.get(), "ALLOW_PRINTING")])

        user_pwd = self.user_pwd_var.get().strip()
        if user_pwd:
            command.extend(["-upwd", user_pwd])

        tsa_url = self.tsa_var.get().strip()
        if tsa_url:
            command.extend(["-ts", tsa_url])

        command.append(str(pdf_path))

        self._log_from_thread("Running command:\n  " + " ".join(f'"{c}"' if " " in c else c for c in command))
        try:
            proc = subprocess.run(command, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            self._log_from_thread(exc.stdout.strip())
            self._log_from_thread(exc.stderr.strip())
            self._show_error("Signing failed", f"JSignPdf returned an error.\n\n{exc.stderr.strip()}")
            self._enable_button()
            return
        except FileNotFoundError as exc:
            self._show_error("Execution error", f"Executable not found: {exc}")
            self._enable_button()
            return

        if proc.stdout:
            self._log_from_thread(proc.stdout.strip())
        if proc.stderr:
            self._log_from_thread(proc.stderr.strip())

        output_file = output_dir / f"{pdf_path.stem}{suffix}.pdf"
        if output_file.exists():
            self._log_from_thread(f"Signed PDF created: {output_file}")
            self._show_info("Success", f"Signed PDF created:\n{output_file}")
        else:
            self._show_info("Completed", "Signing finished. Check the output directory for the signed file.")

        self._enable_button()

    def refresh_cert_list(self, initial: bool = False) -> None:
        aliases = list_cert_aliases()
        if not aliases and DEFAULT_CERT_ALIAS:
            aliases = [DEFAULT_CERT_ALIAS]

        self.alias_combo["values"] = aliases
        if aliases:
            if self.alias_var.get() not in aliases:
                self.alias_var.set(aliases[0])
        else:
            self.alias_var.set("")

        if not initial:
            if aliases:
                self.log(f"Certificate list refreshed ({len(aliases)} found).")
            else:
                self.log("No certificates detected. Enter an alias manually.")

    def _enable_button(self) -> None:
        self.sign_button.configure(state=tk.NORMAL)

    def _log_from_thread(self, message: str) -> None:
        self.root.after(0, self.log, message)

    def _show_error(self, title: str, message: str) -> None:
        self.root.after(0, lambda: messagebox.showerror(title, message))

    def _show_info(self, title: str, message: str) -> None:
        self.root.after(0, lambda: messagebox.showinfo(title, message))


def main() -> None:
    root = tk.Tk()
    SignerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
