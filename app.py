import hashlib
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from lxml import etree

APP_VERSION = "1.4.8"

BG_COLOR = "#eef3f9"
CARD_COLOR = "#ffffff"
BORDER_COLOR = "#cfdae8"
TEXT_PRIMARY = "#1e293b"
TEXT_MUTED = "#64748b"
ACCENT = "#2563eb"
ACCENT_ACTIVE = "#1d4ed8"

DATE_PATTERNS = [
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    re.compile(r"^\d{2}-\d{2}-\d{4}$"),
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),
    re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+\-]\d{2}:\d{2})?$"),
]

EXPECTED_ELEMENT_RE = re.compile(r"Expected is \( ([^)]+) \)\.?")
NOT_ALLOWED_ATTR_RE = re.compile(r"The attribute '([^']+)' is not allowed\.?")
MISSING_ATTR_RE = re.compile(r"The attribute '([^']+)' is required but missing\.?")
INVALID_TYPE_RE = re.compile(r"is not a valid value of the atomic type '([^']+)'\.?")
PATTERN_FACET_RE = re.compile(r"\[facet 'pattern'\]")
ENUM_FACET_RE = re.compile(r"\[facet 'enumeration'\]")

# Common ISO 20022 pain.* sensitive fields to anonymize globally.
# Format: (kind, field_name, short_description), where kind is "element" or "attribute".
COMMON_PAIN_FIELDS: list[tuple[str, str, str]] = [
    ("element", "Nm", "Party name (debtor, creditor, ultimate parties)."),
    ("element", "IBAN", "International bank account number."),
    ("element", "BIC", "Bank identifier code."),
    ("element", "BICFI", "Financial institution BIC."),
    ("element", "Ustrd", "Unstructured remittance text."),
    ("element", "AdrLine", "Address line."),
    ("element", "StrtNm", "Street name."),
    ("element", "BldgNb", "Building number."),
    ("element", "PstCd", "Postal code."),
    ("element", "TwnNm", "Town/city name."),
    ("element", "CtrySubDvsn", "State/region/province."),
    ("element", "Id", "Generic identifier value."),
    ("element", "Othr", "Other/custom identifier."),
    ("element", "PrvtId", "Private person identifier container."),
    ("element", "OrgId", "Organization identifier container."),
    ("element", "MsgId", "Message identifier."),
    ("element", "PmtInfId", "Payment information identifier."),
    ("element", "EndToEndId", "End-to-end transaction identifier."),
    ("element", "InstrId", "Instruction identifier."),
    ("element", "TxId", "Transaction identifier."),
    ("element", "MndtId", "Mandate identifier (direct debit)."),
    ("attribute", "Id", "Identifier used as XML attribute."),
]


class XMLXSDValidatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"XML vs XSD Validator v{APP_VERSION}")
        self.root.geometry("1024x700")
        self.root.minsize(900, 620)

        self.xsd_path: Path | None = None
        self.xml_path: Path | None = None
        self.last_error_entries: list[dict[str, str | int]] = []
        self.status_var = tk.StringVar(value="Select both files to start validation.")
        self.style = ttk.Style(self.root)

        self._configure_theme()
        self._build_ui()

    def _configure_theme(self) -> None:
        self.root.configure(bg=BG_COLOR)
        self.style.theme_use("clam")

        self.style.configure("App.TFrame", background=BG_COLOR)
        self.style.configure("Card.TFrame", background=CARD_COLOR, relief=tk.SOLID, borderwidth=1)
        self.style.configure("CardInner.TFrame", background=CARD_COLOR)

        self.style.configure("Title.TLabel", background=BG_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI Semibold", 20))
        self.style.configure("Subtitle.TLabel", background=BG_COLOR, foreground=TEXT_MUTED, font=("Segoe UI", 10))
        self.style.configure("Section.TLabel", background=CARD_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI Semibold", 11))
        self.style.configure("Field.TLabel", background=CARD_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI", 10))
        self.style.configure("Path.TLabel", background=CARD_COLOR, foreground=TEXT_MUTED, font=("Segoe UI", 10))
        self.style.configure("Status.TLabel", background=BG_COLOR, foreground=TEXT_PRIMARY, font=("Segoe UI Semibold", 10))
        self.style.configure("Hint.TLabel", background=BG_COLOR, foreground=TEXT_MUTED, font=("Segoe UI", 9))

        self.style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(14, 8), foreground="#ffffff", background=ACCENT)
        self.style.map("Primary.TButton", background=[("active", ACCENT_ACTIVE), ("pressed", ACCENT_ACTIVE)])

        self.style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(12, 8))
        self.style.configure("Ghost.TButton", font=("Segoe UI", 10), padding=(12, 8))

        self.style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#dce6f3",
            background=ACCENT,
            bordercolor="#dce6f3",
            lightcolor=ACCENT,
            darkcolor=ACCENT,
        )

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, style="App.TFrame", padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        header = ttk.Frame(container, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="XML vs XSD Validator", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=f"Version {APP_VERSION}", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))

        select_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        select_card.grid(row=1, column=0, sticky="ew")
        select_card.columnconfigure(1, weight=1)

        ttk.Label(select_card, text="Files", style="Section.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(select_card, text="XSD schema", style="Field.TLabel", width=12).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        self.xsd_label = ttk.Label(select_card, text="No file selected", style="Path.TLabel")
        self.xsd_label.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(select_card, text="Browse", command=self.select_xsd, style="Secondary.TButton").grid(row=1, column=2, padx=(10, 0), pady=4)

        ttk.Label(select_card, text="XML file", style="Field.TLabel", width=12).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)
        self.xml_label = ttk.Label(select_card, text="No file selected", style="Path.TLabel")
        self.xml_label.grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Button(select_card, text="Browse", command=self.select_xml, style="Secondary.TButton").grid(row=2, column=2, padx=(10, 0), pady=4)

        controls = ttk.Frame(container, style="App.TFrame")
        controls.grid(row=2, column=0, sticky="ew", pady=12)
        controls.columnconfigure(5, weight=1)
        ttk.Button(controls, text="Validate", command=self.validate, style="Primary.TButton").grid(row=0, column=0, sticky="w")
        ttk.Button(controls, text="Bulk validate", command=self.bulk_validate, style="Secondary.TButton").grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.details_button = ttk.Button(controls, text="Show details", command=self.show_details, state=tk.DISABLED, style="Secondary.TButton")
        self.details_button.grid(row=0, column=2, sticky="w", padx=(8, 0))

        self.anonymize_button = ttk.Button(controls, text="Anonymize XML", command=self.open_anonymize_window, style="Ghost.TButton")
        self.anonymize_button.grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(controls, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=5, sticky="e")

        output_card = ttk.Frame(container, style="Card.TFrame", padding=1)
        output_card.grid(row=3, column=0, sticky="nsew")
        output_card.rowconfigure(1, weight=1)
        output_card.columnconfigure(0, weight=1)

        top_bar = ttk.Frame(output_card, style="CardInner.TFrame")
        top_bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(top_bar, text="Validation output", style="Section.TLabel").pack(side=tk.LEFT, padx=12, pady=(10, 8))
        ttk.Label(top_bar, text="Monospace stream", style="Hint.TLabel").pack(side=tk.RIGHT, padx=12, pady=(10, 8))

        output_frame = ttk.Frame(output_card, style="CardInner.TFrame")
        output_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)

        self.output = tk.Text(
            output_frame,
            wrap=tk.WORD,
            font=("Cascadia Mono", 10),
            bg="#f8fbff",
            fg="#0f172a",
            insertbackground="#0f172a",
            relief=tk.FLAT,
            padx=12,
            pady=10,
        )
        self.output.grid(row=0, column=0, sticky="nsew")

        self.watermark = tk.Label(
            self.output,
            text="XML vs XSD",
            font=("Segoe UI Semibold", 42),
            fg="#d6e0ee",
            bg=self.output.cget("bg"),
        )
        self.watermark.place(relx=0.5, rely=0.5, anchor="center")

        scrollbar = ttk.Scrollbar(output_frame, command=self.output.yview)
        self.output.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._toggle_watermark()

    def _show_warning(self, title: str, text: str, parent: tk.Misc | None = None) -> None:
        messagebox.showwarning(title, text, parent=parent or self.root)

    def _show_info(self, title: str, text: str, parent: tk.Misc | None = None) -> None:
        messagebox.showinfo(title, text, parent=parent or self.root)

    def _show_error(self, title: str, text: str, parent: tk.Misc | None = None) -> None:
        messagebox.showerror(title, text, parent=parent or self.root)

    def select_xsd(self) -> None:
        path = filedialog.askopenfilename(title="Select XSD Schema", filetypes=[("XSD files", "*.xsd"), ("All files", "*.*")])
        if path:
            self.xsd_path = Path(path)
            self.xsd_label.config(text=str(self.xsd_path))
            self.status_var.set("XSD selected. Choose XML file next.")

    def select_xml(self) -> None:
        path = filedialog.askopenfilename(title="Select XML File", filetypes=[("XML files", "*.xml"), ("All files", "*.*")])
        if path:
            self.xml_path = Path(path)
            self.xml_label.config(text=str(self.xml_path))
            self._offer_pretty_format_on_upload(self.xml_path)
            self.status_var.set("XML selected. Ready to validate.")

    def validate(self) -> None:
        self.output.delete("1.0", tk.END)
        self._toggle_watermark()
        self.details_button.config(state=tk.DISABLED)
        self.last_error_entries = []

        if not self.xsd_path or not self.xml_path:
            self._show_warning("Missing files", "Please select both XSD and XML files.")
            self.status_var.set("Select both files before validation.")
            return

        try:
            schema = etree.XMLSchema(etree.parse(str(self.xsd_path)))
        except (etree.XMLSyntaxError, etree.XMLSchemaParseError, OSError) as exc:
            self._write(f"XSD could not be loaded:\n{exc}\n")
            self.status_var.set("XSD parse failed.")
            return

        try:
            xml_doc = etree.parse(str(self.xml_path))
        except (etree.XMLSyntaxError, OSError) as exc:
            self._write(f"XML could not be loaded:\n{exc}\n")
            self.status_var.set("XML parse failed.")
            if isinstance(exc, etree.XMLSyntaxError):
                self.last_error_entries = [{
                    "line": exc.lineno or 1,
                    "column": getattr(exc, "position", (1, 1))[1],
                    "message": str(exc),
                    "domain": "XMLSyntax",
                    "type": "XMLSyntaxError",
                    "hint": self._build_hint(str(exc), "XMLSyntax", "XMLSyntaxError"),
                }]
                self.details_button.config(state=tk.NORMAL)
            return

        if schema.validate(xml_doc):
            self._write("✅ XML is valid against the selected XSD.\n")
            self.status_var.set("Validation passed.")
            return

        self._write("❌ XML is NOT valid. Errors:\n\n")
        self.status_var.set("Validation failed. Review error details.")
        for entry in schema.error_log:
            self.last_error_entries.append({
                "line": entry.line,
                "column": entry.column,
                "message": entry.message,
                "domain": entry.domain_name,
                "type": entry.type_name,
                "hint": self._build_hint(entry.message, entry.domain_name, entry.type_name),
            })
            self._write(f"Line {entry.line}, Column {entry.column}: {entry.message} (Domain: {entry.domain_name}, Type: {entry.type_name})\n")

        self.details_button.config(state=tk.NORMAL)

    def bulk_validate(self) -> None:
        self.output.delete("1.0", tk.END)
        self._toggle_watermark()
        self.details_button.config(state=tk.DISABLED)
        self.last_error_entries = []

        if not self.xsd_path:
            self._show_warning("Missing XSD", "Please select an XSD schema first.")
            self.status_var.set("Select XSD before bulk validation.")
            return

        xml_paths = filedialog.askopenfilenames(
            title="Select XML files for bulk validation",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if not xml_paths:
            self.status_var.set("Bulk validation canceled.")
            return

        try:
            schema = etree.XMLSchema(etree.parse(str(self.xsd_path)))
        except (etree.XMLSyntaxError, etree.XMLSchemaParseError, OSError) as exc:
            self._write(f"XSD could not be loaded:\n{exc}\n")
            self.status_var.set("XSD parse failed.")
            return

        total = len(xml_paths)
        passed = 0
        failed = 0
        parse_failed = 0

        self._write(f"Bulk validation started. Files: {total}\n")
        self._write(f"Schema: {self.xsd_path}\n\n")

        for raw_path in xml_paths:
            path = Path(raw_path)
            try:
                xml_doc = etree.parse(str(path))
            except (etree.XMLSyntaxError, OSError) as exc:
                parse_failed += 1
                self._write(f"[ERROR] {path}\n")
                self._write(f"  Could not load XML: {exc}\n\n")
                continue

            if schema.validate(xml_doc):
                passed += 1
                self._write(f"[PASS]  {path}\n")
                continue

            failed += 1
            self._write(f"[FAIL]  {path}\n")
            for entry in schema.error_log:
                self._write(f"  Line {entry.line}, Column {entry.column}: {entry.message}\n")
            self._write("\n")

        self._write("Summary:\n")
        self._write(f"  Total: {total}\n")
        self._write(f"  Passed: {passed}\n")
        self._write(f"  Failed: {failed}\n")
        self._write(f"  Parse errors: {parse_failed}\n")

        if failed == 0 and parse_failed == 0:
            self.status_var.set(f"Bulk validation passed for all {total} files.")
        else:
            self.status_var.set(f"Bulk validation done. Passed: {passed}, failed: {failed}, parse errors: {parse_failed}.")

    def show_details(self) -> None:
        if not self.xml_path or not self.last_error_entries:
            self._show_warning("No details", "Run validation first and make sure there are errors.")
            return

        xml_text = self._read_xml_for_editor(self.xml_path)
        win = tk.Toplevel(self.root)
        win.title("XML Error Details")
        win.geometry("1200x700")
        win.configure(bg=BG_COLOR)

        paned = ttk.Panedwindow(win, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned, style="App.TFrame")
        right = ttk.Frame(paned, style="Card.TFrame", padding=8)
        paned.add(left, weight=4)
        paned.add(right, weight=2)

        ttk.Label(left, text="XML (editable)", style="Section.TLabel").pack(fill=tk.X, padx=8, pady=(8, 4))
        xml_editor = tk.Text(
            left,
            wrap=tk.NONE,
            font=("Cascadia Mono", 10),
            undo=True,
            bg="#f8fbff",
            fg="#0f172a",
            insertbackground="#0f172a",
            relief=tk.FLAT,
            padx=10,
            pady=8,
        )
        xml_editor.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        xml_editor.insert("1.0", xml_text)

        xml_controls = ttk.Frame(left, style="App.TFrame")
        xml_controls.pack(fill=tk.X, padx=8, pady=(0, 8))

        sync_guard = {"active": False}
        rename_context = {"old_name": ""}
        all_tags_var = tk.BooleanVar(value=False)

        def index_to_offset(index: str) -> int:
            return int(xml_editor.count("1.0", index, "chars")[0])

        def offset_to_index(offset: int) -> str:
            return f"1.0+{offset}c"

        def parse_tag_tokens(text: str) -> list[dict[str, int | str | bool]]:
            tokens: list[dict[str, int | str | bool]] = []
            tag_re = re.compile(r"<(?P<closing>/)?(?P<name>[A-Za-z_][\w:.\-]*)(?P<tail>[^<>]*?)?>", re.DOTALL)
            for match in tag_re.finditer(text):
                closing = bool(match.group("closing"))
                name = match.group("name")
                tail = match.group("tail") or ""
                self_closing = (not closing) and tail.rstrip().endswith("/")
                name_start = match.start("name")
                name_end = match.end("name")
                tokens.append({
                    "start": match.start(),
                    "end": match.end(),
                    "name_start": name_start,
                    "name_end": name_end,
                    "name": name,
                    "closing": closing,
                    "self_closing": self_closing,
                })
            return tokens

        def tag_context_at_cursor(text: str, cursor_offset: int) -> tuple[int, dict[str, int | str | bool]] | tuple[None, None]:
            tokens = parse_tag_tokens(text)
            for idx, token in enumerate(tokens):
                if int(token["name_start"]) <= cursor_offset <= int(token["name_end"]):
                    return idx, token
            return None, None

        def build_structural_pairs(tokens: list[dict[str, int | str | bool]]) -> dict[int, int]:
            pairs: dict[int, int] = {}
            stack: list[int] = []
            for idx, token in enumerate(tokens):
                if bool(token["self_closing"]):
                    continue
                if bool(token["closing"]):
                    if stack:
                        open_idx = stack.pop()
                        pairs[open_idx] = idx
                        pairs[idx] = open_idx
                else:
                    stack.append(idx)
            return pairs

        def sync_paired_tag(_event=None) -> None:
            if sync_guard["active"]:
                return

            text = xml_editor.get("1.0", tk.END)
            cursor = index_to_offset("insert")
            token_idx, token = tag_context_at_cursor(text, cursor)
            if token is None:
                return
            if bool(token["self_closing"]):
                return
            new_name = str(token["name"])
            old_name = str(rename_context.get("old_name", "") or "")
            tokens = parse_tag_tokens(text)
            pairs = build_structural_pairs(tokens)
            partner_idx = pairs.get(token_idx)
            counterpart = tokens[partner_idx] if partner_idx is not None else None

            # Fallback for cases where key-press capture missed: infer previous name
            # from the opposite paired tag that still has the original name.
            if all_tags_var.get() and (not old_name or old_name == new_name) and counterpart is not None:
                counterpart_name = str(counterpart["name"])
                if counterpart_name != new_name:
                    old_name = counterpart_name

            if old_name and old_name != new_name and all_tags_var.get():
                matches = [t for t in tokens if str(t["name"]) == old_name]
                if matches:
                    insert_before = xml_editor.index("insert")
                    sync_guard["active"] = True
                    try:
                        for t in reversed(matches):
                            xml_editor.delete(offset_to_index(int(t["name_start"])), offset_to_index(int(t["name_end"])))
                            xml_editor.insert(offset_to_index(int(t["name_start"])), new_name)
                        xml_editor.mark_set("insert", insert_before)
                    finally:
                        sync_guard["active"] = False
                rename_context["old_name"] = ""
                return

            if counterpart is None:
                return
            if str(counterpart["name"]) == new_name:
                return

            insert_before = xml_editor.index("insert")
            sync_guard["active"] = True
            try:
                xml_editor.delete(offset_to_index(int(counterpart["name_start"])), offset_to_index(int(counterpart["name_end"])))
                xml_editor.insert(offset_to_index(int(counterpart["name_start"])), new_name)
                xml_editor.mark_set("insert", insert_before)
            finally:
                sync_guard["active"] = False

        def capture_tag_name_before_edit(_event=None) -> None:
            if sync_guard["active"]:
                return
            text = xml_editor.get("1.0", tk.END)
            cursor = index_to_offset("insert")
            _idx, token = tag_context_at_cursor(text, cursor)
            if token is None or bool(token["self_closing"]):
                rename_context["old_name"] = ""
                return
            rename_context["old_name"] = str(token["name"])

        def save_details_xml() -> None:
            suggested_name = "edited.xml"
            if self.xml_path is not None:
                suggested_name = f"{self.xml_path.stem}_edited.xml"

            target = filedialog.asksaveasfilename(
                title="Save edited XML",
                defaultextension=".xml",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
                initialfile=suggested_name,
                parent=win,
            )
            if not target:
                return

            edited_text = xml_editor.get("1.0", tk.END)
            try:
                Path(target).write_text(edited_text, encoding="utf-8")
            except OSError as exc:
                self._show_error("Save failed", f"Could not save edited XML:\n{exc}", parent=win)
                return

            if not self.xsd_path:
                self._show_info("Saved", f"Edited XML saved to:\n{target}\n\nNo XSD selected for recheck.", parent=win)
                return

            try:
                schema = etree.XMLSchema(etree.parse(str(self.xsd_path)))
                parser = etree.XMLParser(remove_blank_text=False)
                xml_doc = etree.fromstring(edited_text.encode("utf-8"), parser=parser).getroottree()
            except (etree.XMLSyntaxError, etree.XMLSchemaParseError, OSError) as exc:
                parse_line = 1
                parse_col = 1
                if isinstance(exc, etree.XMLSyntaxError):
                    parse_line = exc.lineno or 1
                    parse_col = getattr(exc, "position", (1, 1))[1]
                refresh_error_panel([{
                    "line": parse_line,
                    "column": parse_col,
                    "message": str(exc),
                    "domain": "XMLSyntax",
                    "type": "XMLSyntaxError",
                    "hint": self._build_hint(str(exc), "XMLSyntax", "XMLSyntaxError"),
                }])
                self.status_var.set("Validation failed after save.")
                self._show_warning(
                    "Saved with validation issue",
                    f"Edited XML saved to:\n{target}\n\nCould not recheck against XSD:\n{exc}",
                    parent=win,
                )
                return

            if schema.validate(xml_doc):
                refresh_error_panel([])
                self.status_var.set("Validation passed after save.")
                self._show_info("Saved and valid", f"Edited XML saved to:\n{target}\n\nSchema recheck passed.", parent=win)
            else:
                errors = list(schema.error_log)
                refreshed_entries: list[dict[str, str | int]] = []
                for entry in errors:
                    refreshed_entries.append({
                        "line": entry.line,
                        "column": entry.column,
                        "message": entry.message,
                        "domain": entry.domain_name,
                        "type": entry.type_name,
                        "hint": self._build_hint(entry.message, entry.domain_name, entry.type_name),
                    })
                refresh_error_panel(refreshed_entries)
                self.status_var.set("Validation failed after save.")
                preview = "\n".join(
                    f"Line {entry.line}, Col {entry.column}: {entry.message}" for entry in errors[:3]
                )
                suffix = "\n..." if len(errors) > 3 else ""
                self._show_warning(
                    "Saved but schema failed",
                    f"Edited XML saved to:\n{target}\n\nSchema recheck found {len(errors)} error(s):\n{preview}{suffix}",
                    parent=win,
                )

        ttk.Button(xml_controls, text="Save edited XML", command=save_details_xml, style="Secondary.TButton").pack(side=tk.LEFT)
        ttk.Checkbutton(xml_controls, text="All tags", variable=all_tags_var).pack(side=tk.LEFT, padx=(10, 0))
        xml_editor.bind("<KeyPress>", capture_tag_name_before_edit, add="+")
        xml_editor.bind("<KeyRelease>", sync_paired_tag, add="+")

        ttk.Label(right, text="Drag the divider to resize sections", style="Hint.TLabel").pack(fill=tk.X, pady=(2, 6))

        right_split = ttk.Panedwindow(right, orient=tk.VERTICAL)
        right_split.pack(fill=tk.BOTH, expand=True)

        errors_frame = ttk.Frame(right, style="CardInner.TFrame", padding=2)
        details_frame = ttk.Frame(right, style="CardInner.TFrame", padding=2)
        right_split.add(errors_frame, weight=3)
        right_split.add(details_frame, weight=2)

        ttk.Label(errors_frame, text="Errors", style="Section.TLabel").pack(fill=tk.X, pady=(2, 4))
        error_list = tk.Listbox(
            errors_frame,
            bg="#f8fafc",
            fg=TEXT_PRIMARY,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            selectbackground="#cfe8ff",
            font=("Segoe UI", 10),
        )
        error_list.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        ttk.Label(details_frame, text="Selected error details", style="Section.TLabel").pack(fill=tk.X, pady=(2, 4))
        details_panel = tk.Text(
            details_frame,
            wrap=tk.WORD,
            height=8,
            font=("Cascadia Mono", 10),
            state=tk.DISABLED,
            relief=tk.FLAT,
            bg="#f8fafc",
            fg=TEXT_PRIMARY,
            padx=8,
            pady=8,
        )
        details_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 2))

        xml_editor.tag_configure("error_line", background="#ffe7e7")

        def on_select(_event=None) -> None:
            selected = error_list.curselection()
            if not selected:
                return
            if selected[0] >= len(self.last_error_entries):
                return
            err = self.last_error_entries[selected[0]]
            xml_editor.tag_remove("error_line", "1.0", tk.END)
            line_val = err.get("line")
            if isinstance(line_val, int) and line_val > 0:
                start = f"{line_val}.0"
                end = f"{line_val}.0 lineend"
                xml_editor.tag_add("error_line", start, end)
                xml_editor.see(start)

            details_panel.config(state=tk.NORMAL)
            details_panel.delete("1.0", tk.END)
            details_panel.insert(
                tk.END,
                f"Line: {err['line']}\n"
                f"Column: {err['column']}\n"
                f"Domain: {err['domain']}\n"
                f"Type: {err['type']}\n\n"
                f"Message:\n{err['message']}\n\n"
                f"Quick fix hint:\n{err.get('hint', 'No hint available.')}",
            )
            details_panel.config(state=tk.DISABLED)

        def refresh_error_panel(entries: list[dict[str, str | int]]) -> None:
            self.last_error_entries = entries
            error_list.delete(0, tk.END)
            xml_editor.tag_remove("error_line", "1.0", tk.END)

            details_panel.config(state=tk.NORMAL)
            details_panel.delete("1.0", tk.END)
            details_panel.config(state=tk.DISABLED)

            if not entries:
                error_list.insert(tk.END, "No schema errors.")
                return

            for idx, err in enumerate(entries, 1):
                error_list.insert(tk.END, f"{idx}. Line {err['line']}, Col {err['column']} - {str(err['message'])[:70]}")

            error_list.selection_clear(0, tk.END)
            error_list.selection_set(0)
            on_select()

        error_list.bind("<<ListboxSelect>>", on_select)
        refresh_error_panel(self.last_error_entries)

    def open_anonymize_window(self) -> None:
        if not self.xml_path:
            self._show_warning("Missing XML", "Please select an XML file first.")
            return

        xml_text = self._read_xml_for_editor(self.xml_path)

        win = tk.Toplevel(self.root)
        win.title("Anonymize XML")
        win.geometry("1200x750")
        win.configure(bg=BG_COLOR)

        selected_lines: set[int] = set()

        top_controls = ttk.Frame(win, style="App.TFrame")
        top_controls.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(
            top_controls,
            text="Select lines containing tags/attributes to anonymize. Selected names are updated globally in the whole file.",
            style="Subtitle.TLabel",
            anchor="w",
        ).pack(side=tk.LEFT)

        editor_frame = ttk.Frame(win, style="Card.TFrame", padding=8)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        gutter = tk.Text(
            editor_frame,
            width=8,
            wrap=tk.NONE,
            font=("Cascadia Mono", 10),
            state=tk.DISABLED,
            bg="#e2e8f0",
            fg=TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        gutter.pack(side=tk.LEFT, fill=tk.Y)

        editor = tk.Text(
            editor_frame,
            wrap=tk.NONE,
            font=("Cascadia Mono", 10),
            undo=True,
            bg="#f8fbff",
            fg="#0f172a",
            insertbackground="#0f172a",
            relief=tk.FLAT,
            padx=10,
            pady=8,
        )
        editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        editor.insert("1.0", xml_text)

        scrollbar = ttk.Scrollbar(editor_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def yscroll_command(*args):
            editor.yview(*args)
            gutter.yview(*args)

        def on_editor_scroll(first: str, last: str):
            scrollbar.set(first, last)
            gutter.yview_moveto(first)

        editor.configure(yscrollcommand=on_editor_scroll)
        gutter.configure(yscrollcommand=lambda first, last: None)
        scrollbar.configure(command=yscroll_command)

        editor.tag_configure("selected_lines", background="#dbeafe")
        gutter.tag_configure("selected_lines", background="#cbd5e1")

        def render_gutter() -> None:
            line_count = int(editor.index("end-1c").split(".")[0])
            line_digits = max(1, len(str(line_count)))
            # marker "[ ]" + space + full line number width
            gutter.config(width=max(8, line_digits + 4))
            gutter.config(state=tk.NORMAL)
            gutter.delete("1.0", tk.END)
            for line_no in range(1, line_count + 1):
                mark = "[x]" if line_no in selected_lines else "[ ]"
                gutter.insert(tk.END, f"{mark} {line_no:>{line_digits}}\n")
            gutter.config(state=tk.DISABLED)
            refresh_highlights()

        def refresh_highlights() -> None:
            editor.tag_remove("selected_lines", "1.0", tk.END)
            gutter.tag_remove("selected_lines", "1.0", tk.END)
            for line_no in selected_lines:
                editor.tag_add("selected_lines", f"{line_no}.0", f"{line_no}.0 lineend")
                gutter.tag_add("selected_lines", f"{line_no}.0", f"{line_no}.0 lineend")

        def toggle_line_by_number(line_no: int) -> None:
            if line_no in selected_lines:
                selected_lines.remove(line_no)
            else:
                selected_lines.add(line_no)
            render_gutter()

        def toggle_line(event) -> str:
            index = gutter.index(f"@{event.x},{event.y}")
            line_no = int(index.split(".")[0])
            toggle_line_by_number(line_no)
            return "break"

        def toggle_line_from_editor_click(event) -> None:
            index = editor.index(f"@{event.x},{event.y}")
            line_no = int(index.split(".")[0])
            toggle_line_by_number(line_no)

        def clear_invalid_selected_lines() -> None:
            max_line = int(editor.index("end-1c").split(".")[0])
            selected_lines.intersection_update(set(range(1, max_line + 1)))

        def on_editor_key_release(_event=None) -> None:
            clear_invalid_selected_lines()
            render_gutter()

        gutter.bind("<Button-1>", toggle_line)
        editor.bind("<Button-1>", toggle_line_from_editor_click, add="+")
        editor.bind("<KeyRelease>", on_editor_key_release)

        render_gutter()

        bottom_controls = ttk.Frame(win, style="App.TFrame")
        bottom_controls.pack(fill=tk.X, padx=8, pady=(4, 8))

        def parse_editor_xml() -> etree._ElementTree:
            parser = etree.XMLParser(remove_blank_text=False)
            return etree.fromstring(editor.get("1.0", tk.END).encode("utf-8"), parser=parser).getroottree()

        def refresh_editor(tree: etree._ElementTree) -> None:
            updated = etree.tostring(tree, pretty_print=True, encoding="utf-8", xml_declaration=True).decode("utf-8")
            editor.delete("1.0", tk.END)
            editor.insert("1.0", updated)
            selected_lines.clear()
            render_gutter()

        def anonymize_all() -> None:
            try:
                tree = parse_editor_xml()
                self._anonymize_tree(tree)
                refresh_editor(tree)
                self._show_info("Anonymized", "All eligible values were anonymized (dates preserved).", parent=win)
            except Exception as exc:
                self._show_error("Anonymize failed", f"Could not anonymize XML:\n{exc}", parent=win)

        def anonymize_selected_lines() -> None:
            try:
                if not selected_lines:
                    self._show_warning("No lines selected", "Tick one or more lines in the left marker column first.", parent=win)
                    return

                tree = parse_editor_xml()
                selected_elements, selected_attributes = self._collect_targets_from_lines(tree, selected_lines)
                if not selected_elements and not selected_attributes:
                    self._show_info(
                        "No matching tags",
                        "No element text or attributes were found on selected lines.",
                        parent=win,
                    )
                    return

                changed = self._anonymize_tree_by_targets(
                    tree,
                    target_elements=selected_elements,
                    target_attributes=selected_attributes,
                )
                refresh_editor(tree)

                if changed == 0:
                    self._show_info("No changes", "Selected tags/attributes were found, but no eligible values were changed.", parent=win)
                else:
                    targets = []
                    if selected_elements:
                        targets.append(f"tags: {', '.join(sorted(selected_elements))}")
                    if selected_attributes:
                        targets.append(f"attributes: {', '.join(sorted(selected_attributes))}")
                    self._show_info(
                        "Anonymized",
                        f"Updated fields: {changed}\nApplied globally for selected {', '.join(targets)}.",
                        parent=win,
                    )
            except Exception as exc:
                self._show_error("Anonymize failed", f"Could not anonymize selected lines:\n{exc}", parent=win)

        def anonymize_common_fields() -> None:
            try:
                detection_tree = parse_editor_xml()
            except Exception as exc:
                self._show_error("Analyze failed", f"Could not inspect XML for common fields:\n{exc}", parent=win)
                return

            present_elements: set[str] = set()
            present_attributes: set[str] = set()
            for elem in detection_tree.getroot().iter():
                present_elements.add(self._local_name(elem.tag))
                for attr_name in elem.attrib.keys():
                    present_attributes.add(self._local_name(attr_name))

            available_fields = [
                (kind, field_name, description)
                for kind, field_name, description in COMMON_PAIN_FIELDS
                if (kind == "element" and field_name in present_elements)
                or (kind == "attribute" and field_name in present_attributes)
            ]

            if not available_fields:
                self._show_info(
                    "No common fields found",
                    "None of the configured common pain fields were found in this XML.",
                    parent=win,
                )
                return

            picker = tk.Toplevel(win)
            picker.title("Common pain fields")
            picker.geometry("760x520")
            picker.configure(bg=BG_COLOR)
            picker.transient(win)
            picker.grab_set()

            ttk.Label(
                picker,
                text="Select common pain fields to anonymize",
                style="Section.TLabel",
            ).pack(fill=tk.X, padx=12, pady=(12, 4))
            ttk.Label(
                picker,
                text="All fields are selected by default. Untick the ones you want to keep unchanged.",
                style="Subtitle.TLabel",
            ).pack(fill=tk.X, padx=12, pady=(0, 10))

            list_frame = ttk.Frame(picker, style="Card.TFrame", padding=8)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
            list_frame.columnconfigure(0, weight=1)
            list_frame.rowconfigure(0, weight=1)

            canvas = tk.Canvas(list_frame, bg="#f8fbff", highlightthickness=0)
            scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
            rows = ttk.Frame(canvas, style="CardInner.TFrame")

            canvas.configure(yscrollcommand=scroll.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            scroll.grid(row=0, column=1, sticky="ns")

            row_window = canvas.create_window((0, 0), window=rows, anchor="nw")

            def on_rows_configure(_event=None) -> None:
                canvas.configure(scrollregion=canvas.bbox("all"))

            def on_canvas_configure(event) -> None:
                canvas.itemconfig(row_window, width=event.width)

            rows.bind("<Configure>", on_rows_configure)
            canvas.bind("<Configure>", on_canvas_configure)

            selections: list[tuple[str, str, tk.BooleanVar]] = []
            for kind, field_name, description in available_fields:
                var = tk.BooleanVar(value=True)
                line_text = f"{field_name} ({kind}) - {description}"
                ttk.Checkbutton(rows, text=line_text, variable=var).pack(anchor="w", fill=tk.X, padx=4, pady=2)
                selections.append((kind, field_name, var))

            controls = ttk.Frame(picker, style="App.TFrame")
            controls.pack(fill=tk.X, padx=12, pady=(0, 12))

            def apply_selected_common_fields() -> None:
                target_elements = {name for kind, name, var in selections if kind == "element" and var.get()}
                target_attributes = {name for kind, name, var in selections if kind == "attribute" and var.get()}
                if not target_elements and not target_attributes:
                    self._show_warning("No fields selected", "Please keep at least one field ticked.", parent=picker)
                    return

                try:
                    tree = parse_editor_xml()
                    changed = self._anonymize_tree_by_targets(
                        tree,
                        target_elements=target_elements,
                        target_attributes=target_attributes,
                    )
                    refresh_editor(tree)
                    picker.destroy()

                    if changed == 0:
                        self._show_info(
                            "No changes",
                            "No selected common pain fields were found with eligible values to anonymize.",
                            parent=win,
                        )
                    else:
                        self._show_info(
                            "Anonymized",
                            f"Anonymized selected common pain fields globally. Updated fields: {changed}.",
                            parent=win,
                        )
                except Exception as exc:
                    self._show_error("Anonymize failed", f"Could not anonymize common fields:\n{exc}", parent=picker)

            ttk.Button(controls, text="Anonymize selected", command=apply_selected_common_fields, style="Primary.TButton").pack(side=tk.LEFT)
            ttk.Button(controls, text="Cancel", command=picker.destroy, style="Secondary.TButton").pack(side=tk.RIGHT)

        def save_anonymized() -> None:
            suggested_name = "anonymized.xml"
            if self.xml_path is not None:
                suggested_name = f"{self.xml_path.stem}_anonim.xml"

            target = filedialog.asksaveasfilename(
                title="Save anonymized XML",
                defaultextension=".xml",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
                initialfile=suggested_name,
                parent=win,
            )
            if not target:
                return
            Path(target).write_text(editor.get("1.0", tk.END), encoding="utf-8")
            self._show_info("Saved", f"Anonymized XML saved to:\n{target}", parent=win)

        ttk.Button(bottom_controls, text="Anonymize all", command=anonymize_all, style="Primary.TButton").pack(side=tk.LEFT)
        ttk.Button(bottom_controls, text="Anonymize common pain fields", command=anonymize_common_fields, style="Secondary.TButton").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(bottom_controls, text="Anonymize selected tags globally", command=anonymize_selected_lines, style="Secondary.TButton").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(bottom_controls, text="Save anonymized XML", command=save_anonymized, style="Secondary.TButton").pack(side=tk.RIGHT)

    def _is_date_value(self, value: str) -> bool:
        normalized = value.strip()
        return any(pattern.match(normalized) for pattern in DATE_PATTERNS)

    def _anonymize_value(self, value: str) -> str:
        if not value.strip() or self._is_date_value(value):
            return value

        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        output = []
        d_idx = 0

        for ch in value:
            if ch.isupper():
                output.append(chr(ord("A") + int(digest[d_idx % len(digest)], 16) % 26))
                d_idx += 1
            elif ch.islower():
                output.append(chr(ord("a") + int(digest[d_idx % len(digest)], 16) % 26))
                d_idx += 1
            elif ch.isdigit():
                output.append(str(int(digest[d_idx % len(digest)], 16) % 10))
                d_idx += 1
            else:
                output.append(ch)

        return "".join(output)

    def _anonymize_tree(self, tree: etree._ElementTree, target_lines: set[int] | None = None) -> int:
        changed = 0
        for elem in tree.getroot().iter():
            apply_here = target_lines is None or (elem.sourceline in target_lines if elem.sourceline else False)
            if not apply_here:
                continue

            if elem.text is not None:
                anon = self._anonymize_value(elem.text)
                if anon != elem.text:
                    elem.text = anon
                    changed += 1

            for attr_name, attr_value in list(elem.attrib.items()):
                anon = self._anonymize_value(attr_value)
                if anon != attr_value:
                    elem.attrib[attr_name] = anon
                    changed += 1

        return changed

    def _collect_targets_from_lines(self, tree: etree._ElementTree, lines: set[int]) -> tuple[set[str], set[str]]:
        target_elements: set[str] = set()
        target_attributes: set[str] = set()

        for elem in tree.getroot().iter():
            if elem.sourceline not in lines:
                continue

            if elem.text and elem.text.strip():
                target_elements.add(self._local_name(elem.tag))
            for attr_name in elem.attrib.keys():
                target_attributes.add(self._local_name(attr_name))

        return target_elements, target_attributes

    def _anonymize_tree_by_targets(
        self,
        tree: etree._ElementTree,
        target_elements: set[str],
        target_attributes: set[str],
    ) -> int:
        changed = 0
        for elem in tree.getroot().iter():
            if self._local_name(elem.tag) in target_elements and elem.text is not None:
                anon = self._anonymize_value(elem.text)
                if anon != elem.text:
                    elem.text = anon
                    changed += 1

            for attr_name, attr_value in list(elem.attrib.items()):
                if self._local_name(attr_name) not in target_attributes:
                    continue
                anon = self._anonymize_value(attr_value)
                if anon != attr_value:
                    elem.attrib[attr_name] = anon
                    changed += 1

        return changed

    def _local_name(self, name: str) -> str:
        if name.startswith("{"):
            return name.split("}", maxsplit=1)[1]
        return name

    def _pretty_format_xml_bytes(self, xml_bytes: bytes) -> str | None:
        try:
            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.fromstring(xml_bytes, parser=parser)
            return etree.tostring(root, pretty_print=True, encoding="utf-8", xml_declaration=True).decode("utf-8")
        except (etree.XMLSyntaxError, ValueError):
            return None

    def _read_xml_for_editor(self, path: Path) -> str:
        try:
            pretty = self._pretty_format_xml_bytes(path.read_bytes())
            if pretty is not None:
                return pretty
        except OSError:
            pass
        return path.read_text(encoding="utf-8", errors="replace")

    def _offer_pretty_format_on_upload(self, path: Path) -> None:
        try:
            xml_bytes = path.read_bytes()
        except OSError:
            return

        # Prompt only for likely minified files (single-line or almost single-line).
        if xml_bytes.count(b"\n") > 1:
            return

        pretty = self._pretty_format_xml_bytes(xml_bytes)
        if pretty is None:
            return

        current_text = xml_bytes.decode("utf-8", errors="replace")
        if pretty.strip() == current_text.strip():
            return

        if messagebox.askyesno(
            "Pretty format XML",
            "This XML looks minified/single-line.\n\nDo you want to pretty-format and save it now?",
            parent=self.root,
        ):
            try:
                path.write_text(pretty, encoding="utf-8")
                self.status_var.set("XML selected and pretty-formatted.")
            except OSError as exc:
                self._show_error("Format failed", f"Could not save formatted XML:\n{exc}")

    def _build_hint(self, message: str, domain: str, error_type: str) -> str:
        msg = message.strip()
        msg_lower = msg.lower()

        expected_match = EXPECTED_ELEMENT_RE.search(msg)
        if expected_match:
            expected = expected_match.group(1).replace("'", "").replace("{", "").replace("}", "")
            return f"Element/order mismatch. Replace this element with one of: {expected}, or move it to the position expected by the schema."

        not_allowed_attr = NOT_ALLOWED_ATTR_RE.search(msg)
        if not_allowed_attr:
            attr = not_allowed_attr.group(1)
            return f"Attribute '{attr}' is not permitted here. Remove it or rename it to an attribute allowed for this element in the XSD."

        missing_attr = MISSING_ATTR_RE.search(msg)
        if missing_attr:
            attr = missing_attr.group(1)
            return f"Required attribute '{attr}' is missing. Add it to this element with a value matching the XSD type."

        invalid_type = INVALID_TYPE_RE.search(msg)
        if invalid_type:
            atomic_type = invalid_type.group(1)
            if atomic_type.endswith("date"):
                return "Invalid date value. Use ISO format YYYY-MM-DD (example: 2026-03-02)."
            if atomic_type.endswith("dateTime"):
                return "Invalid datetime value. Use ISO format YYYY-MM-DDThh:mm:ss (optionally with timezone, e.g. Z)."
            if atomic_type.endswith("int") or atomic_type.endswith("integer"):
                return "Invalid integer value. Use digits only, no decimals or text."
            if atomic_type.endswith("decimal"):
                return "Invalid decimal value. Use a numeric value like 12.34."
            return f"Value does not match expected type '{atomic_type}'. Update value to the XSD type format."

        if PATTERN_FACET_RE.search(msg):
            return "Value fails schema pattern. Check allowed format/regex in the XSD and adjust this value to match."

        if ENUM_FACET_RE.search(msg):
            return "Value is outside allowed enumeration. Replace it with one of the schema's permitted values."

        if "no matching global declaration available for the validation root" in msg_lower:
            return "Root element/namespace mismatch. Ensure XML root name and namespace URI match the schema target namespace."

        if "this element is not expected" in msg_lower:
            return "Unexpected element. Verify element name, namespace prefix, and order relative to sibling elements."

        if domain == "XMLSyntax" or error_type == "XMLSyntaxError":
            return "Malformed XML syntax. Check for unclosed tags, invalid characters, and quote mismatches near this line."

        return "Review this node against the XSD definition for element name, namespace, required attributes, and value format."

    def _write(self, text: str) -> None:
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self._toggle_watermark()

    def _toggle_watermark(self) -> None:
        if self.output.get("1.0", tk.END).strip():
            self.watermark.place_forget()
        else:
            self.watermark.place(relx=0.5, rely=0.5, anchor="center")


def main() -> None:
    root = tk.Tk()
    XMLXSDValidatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
