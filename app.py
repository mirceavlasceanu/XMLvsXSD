import hashlib
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from lxml import etree

APP_VERSION = "1.3.0"

DATE_PATTERNS = [
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    re.compile(r"^\d{2}-\d{2}-\d{4}$"),
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),
    re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+\-]\d{2}:\d{2})?$"),
]


class XMLXSDValidatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"XML vs XSD Validator v{APP_VERSION}")
        self.root.geometry("900x600")

        self.xsd_path: Path | None = None
        self.xml_path: Path | None = None
        self.last_error_entries: list[dict[str, str | int]] = []

        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=12, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Validate XML against XSD", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 12))
        tk.Label(container, text=f"Version: {APP_VERSION}", fg="#666666", font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 10))

        xsd_frame = tk.Frame(container)
        xsd_frame.pack(fill=tk.X, pady=4)
        tk.Label(xsd_frame, text="XSD file:", width=12, anchor="w").pack(side=tk.LEFT)
        self.xsd_label = tk.Label(xsd_frame, text="No file selected", anchor="w")
        self.xsd_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(xsd_frame, text="Browse XSD", command=self.select_xsd).pack(side=tk.RIGHT)

        xml_frame = tk.Frame(container)
        xml_frame.pack(fill=tk.X, pady=4)
        tk.Label(xml_frame, text="XML file:", width=12, anchor="w").pack(side=tk.LEFT)
        self.xml_label = tk.Label(xml_frame, text="No file selected", anchor="w")
        self.xml_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(xml_frame, text="Browse XML", command=self.select_xml).pack(side=tk.RIGHT)

        controls = tk.Frame(container)
        controls.pack(anchor="w", pady=12)

        tk.Button(controls, text="Validate", command=self.validate, bg="#0d6efd", fg="white", padx=16, pady=6).pack(side=tk.LEFT)

        self.details_button = tk.Button(controls, text="Show details", command=self.show_details, state=tk.DISABLED, padx=16, pady=6)
        self.details_button.pack(side=tk.LEFT, padx=(8, 0))

        self.anonymize_button = tk.Button(controls, text="Anonymize", command=self.open_anonymize_window, state=tk.NORMAL, padx=16, pady=6)
        self.anonymize_button.pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(container, text="Validation output:", anchor="w").pack(anchor="w")

        output_frame = tk.Frame(container)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.output = tk.Text(output_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True)

        self.watermark = tk.Label(
            self.output,
            text="XML vs XSD",
            font=("Segoe UI", 44, "bold"),
            fg="#d0d0d0",
            bg=self.output.cget("bg"),
        )
        self.watermark.place(relx=0.5, rely=0.5, anchor="center")

        scrollbar = tk.Scrollbar(output_frame, command=self.output.yview)
        self.output.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._toggle_watermark()

    def select_xsd(self) -> None:
        path = filedialog.askopenfilename(title="Select XSD Schema", filetypes=[("XSD files", "*.xsd"), ("All files", "*.*")])
        if path:
            self.xsd_path = Path(path)
            self.xsd_label.config(text=str(self.xsd_path))

    def select_xml(self) -> None:
        path = filedialog.askopenfilename(title="Select XML File", filetypes=[("XML files", "*.xml"), ("All files", "*.*")])
        if path:
            self.xml_path = Path(path)
            self.xml_label.config(text=str(self.xml_path))

    def validate(self) -> None:
        self.output.delete("1.0", tk.END)
        self._toggle_watermark()
        self.details_button.config(state=tk.DISABLED)
        self.last_error_entries = []

        if not self.xsd_path or not self.xml_path:
            messagebox.showwarning("Missing files", "Please select both XSD and XML files.")
            return

        try:
            schema = etree.XMLSchema(etree.parse(str(self.xsd_path)))
        except (etree.XMLSyntaxError, etree.XMLSchemaParseError, OSError) as exc:
            self._write(f"XSD could not be loaded:\n{exc}\n")
            return

        try:
            xml_doc = etree.parse(str(self.xml_path))
        except (etree.XMLSyntaxError, OSError) as exc:
            self._write(f"XML could not be loaded:\n{exc}\n")
            if isinstance(exc, etree.XMLSyntaxError):
                self.last_error_entries = [{
                    "line": exc.lineno or 1,
                    "column": getattr(exc, "position", (1, 1))[1],
                    "message": str(exc),
                    "domain": "XMLSyntax",
                    "type": "XMLSyntaxError",
                }]
                self.details_button.config(state=tk.NORMAL)
            return

        if schema.validate(xml_doc):
            self._write("✅ XML is valid against the selected XSD.\n")
            return

        self._write("❌ XML is NOT valid. Errors:\n\n")
        for entry in schema.error_log:
            self.last_error_entries.append({
                "line": entry.line,
                "column": entry.column,
                "message": entry.message,
                "domain": entry.domain_name,
                "type": entry.type_name,
            })
            self._write(f"Line {entry.line}, Column {entry.column}: {entry.message} (Domain: {entry.domain_name}, Type: {entry.type_name})\n")

        self.details_button.config(state=tk.NORMAL)

    def show_details(self) -> None:
        if not self.xml_path or not self.last_error_entries:
            messagebox.showwarning("No details", "Run validation first and make sure there are errors.")
            return

        xml_text = self.xml_path.read_text(encoding="utf-8", errors="replace")
        win = tk.Toplevel(self.root)
        win.title("XML Error Details")
        win.geometry("1200x700")

        paned = tk.PanedWindow(win, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(paned)
        right = tk.Frame(paned, width=380)
        paned.add(left, stretch="always")
        paned.add(right)

        tk.Label(left, text="XML (editable)", anchor="w").pack(fill=tk.X, padx=8, pady=(8, 2))
        xml_editor = tk.Text(left, wrap=tk.NONE, font=("Consolas", 10), undo=True)
        xml_editor.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        xml_editor.insert("1.0", xml_text)

        tk.Label(right, text="Errors", anchor="w", font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=8, pady=(8, 2))
        error_list = tk.Listbox(right)
        error_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        tk.Label(right, text="Selected error details", anchor="w", font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=8)
        details_panel = tk.Text(right, wrap=tk.WORD, height=8, font=("Consolas", 10), state=tk.DISABLED)
        details_panel.pack(fill=tk.BOTH, padx=8, pady=(2, 8))

        for idx, err in enumerate(self.last_error_entries, 1):
            error_list.insert(tk.END, f"{idx}. Line {err['line']}, Col {err['column']} - {str(err['message'])[:70]}")

        xml_editor.tag_configure("error_line", background="#ffe7e7")

        def on_select(_event=None) -> None:
            selected = error_list.curselection()
            if not selected:
                return
            err = self.last_error_entries[selected[0]]
            line = int(err["line"])
            xml_editor.tag_remove("error_line", "1.0", tk.END)
            start = f"{line}.0"
            end = f"{line}.0 lineend"
            xml_editor.tag_add("error_line", start, end)
            xml_editor.see(start)

            details_panel.config(state=tk.NORMAL)
            details_panel.delete("1.0", tk.END)
            details_panel.insert(tk.END, f"Line: {err['line']}\nColumn: {err['column']}\nDomain: {err['domain']}\nType: {err['type']}\nMessage: {err['message']}")
            details_panel.config(state=tk.DISABLED)

        error_list.bind("<<ListboxSelect>>", on_select)
        if self.last_error_entries:
            error_list.selection_set(0)
            on_select()

    def open_anonymize_window(self) -> None:
        if not self.xml_path:
            messagebox.showwarning("Missing XML", "Please select an XML file first.")
            return

        xml_text = self.xml_path.read_text(encoding="utf-8", errors="replace")

        win = tk.Toplevel(self.root)
        win.title("Anonymize XML")
        win.geometry("1200x750")

        top_controls = tk.Frame(win)
        top_controls.pack(fill=tk.X, padx=8, pady=(8, 4))

        tk.Label(top_controls, text="Choose anonymization mode:", anchor="w").pack(side=tk.LEFT)

        editor = tk.Text(win, wrap=tk.NONE, font=("Consolas", 10), undo=True)
        editor.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        editor.insert("1.0", xml_text)

        editor.tag_configure("selected_lines", background="#fff4cc")

        bottom_controls = tk.Frame(win)
        bottom_controls.pack(fill=tk.X, padx=8, pady=(4, 8))

        def parse_editor_xml() -> etree._ElementTree:
            parser = etree.XMLParser(remove_blank_text=False)
            return etree.fromstring(editor.get("1.0", tk.END).encode("utf-8"), parser=parser).getroottree()

        def refresh_editor(tree: etree._ElementTree) -> None:
            updated = etree.tostring(tree, pretty_print=True, encoding="utf-8", xml_declaration=True).decode("utf-8")
            editor.delete("1.0", tk.END)
            editor.insert("1.0", updated)
            editor.tag_remove("selected_lines", "1.0", tk.END)

        def anonymize_all() -> None:
            try:
                tree = parse_editor_xml()
                self._anonymize_tree(tree)
                refresh_editor(tree)
                messagebox.showinfo("Anonymized", "All eligible values were anonymized (dates preserved).")
            except Exception as exc:
                messagebox.showerror("Anonymize failed", f"Could not anonymize XML:\n{exc}")

        def anonymize_selected_lines() -> None:
            try:
                if not editor.tag_ranges(tk.SEL):
                    messagebox.showwarning("No selection", "Select one or more lines in the XML editor first.")
                    return

                start_line = int(str(editor.index("sel.first")).split(".")[0])
                end_line = int(str(editor.index("sel.last")).split(".")[0])
                selected_lines = set(range(start_line, end_line + 1))

                editor.tag_remove("selected_lines", "1.0", tk.END)
                for ln in selected_lines:
                    editor.tag_add("selected_lines", f"{ln}.0", f"{ln}.0 lineend")

                tree = parse_editor_xml()
                changed = self._anonymize_tree(tree, target_lines=selected_lines)
                refresh_editor(tree)

                if changed == 0:
                    messagebox.showinfo("No changes", "No values matched selected lines for anonymization.")
                else:
                    messagebox.showinfo("Anonymized", f"Anonymized values for selected lines. Updated fields: {changed}.")
            except Exception as exc:
                messagebox.showerror("Anonymize failed", f"Could not anonymize selected lines:\n{exc}")

        def save_anonymized() -> None:
            target = filedialog.asksaveasfilename(
                title="Save anonymized XML",
                defaultextension=".xml",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
            )
            if not target:
                return
            Path(target).write_text(editor.get("1.0", tk.END), encoding="utf-8")
            messagebox.showinfo("Saved", f"Anonymized XML saved to:\n{target}")

        tk.Button(bottom_controls, text="Anonymize all", command=anonymize_all, padx=16, pady=6).pack(side=tk.LEFT)
        tk.Button(bottom_controls, text="Anonymize selected lines", command=anonymize_selected_lines, padx=16, pady=6).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(bottom_controls, text="Save anonymized XML", command=save_anonymized, padx=16, pady=6).pack(side=tk.RIGHT)

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
