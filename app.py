import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from lxml import etree

APP_VERSION = "1.2.0"


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

        tk.Label(
            container,
            text="Validate XML against XSD",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        tk.Label(
            container,
            text=f"Version: {APP_VERSION}",
            fg="#666666",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 10))

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

        tk.Button(
            controls,
            text="Validate",
            command=self.validate,
            bg="#0d6efd",
            fg="white",
            padx=16,
            pady=6,
        ).pack(side=tk.LEFT)

        self.details_button = tk.Button(
            controls,
            text="Show details",
            command=self.show_details,
            state=tk.DISABLED,
            padx=16,
            pady=6,
        )
        self.details_button.pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(container, text="Validation output:", anchor="w").pack(anchor="w")

        output_frame = tk.Frame(container)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.output = tk.Text(output_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True)

        self.watermark = tk.Label(
            self.output,
            text="Kasia",
            font=("Segoe UI", 48, "bold"),
            fg="#d0d0d0",
            bg=self.output.cget("bg"),
        )
        self.watermark.place(relx=0.5, rely=0.5, anchor="center")

        scrollbar = tk.Scrollbar(output_frame, command=self.output.yview)
        self.output.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._toggle_watermark()

    def select_xsd(self) -> None:
        path = filedialog.askopenfilename(
            title="Select XSD Schema",
            filetypes=[("XSD files", "*.xsd"), ("All files", "*.*")],
        )
        if path:
            self.xsd_path = Path(path)
            self.xsd_label.config(text=str(self.xsd_path))

    def select_xml(self) -> None:
        path = filedialog.askopenfilename(
            title="Select XML File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
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
            xsd_doc = etree.parse(str(self.xsd_path))
            schema = etree.XMLSchema(xsd_doc)
        except (etree.XMLSyntaxError, etree.XMLSchemaParseError, OSError) as exc:
            self._write(f"XSD could not be loaded:\n{exc}\n")
            return

        try:
            xml_doc = etree.parse(str(self.xml_path))
        except (etree.XMLSyntaxError, OSError) as exc:
            self._write(f"XML could not be loaded:\n{exc}\n")
            if isinstance(exc, etree.XMLSyntaxError):
                self.last_error_entries = [
                    {
                        "line": exc.lineno or 1,
                        "column": getattr(exc, "position", (1, 1))[1],
                        "message": str(exc),
                        "domain": "XMLSyntax",
                        "type": "XMLSyntaxError",
                    }
                ]
                self.details_button.config(state=tk.NORMAL)
            return

        is_valid = schema.validate(xml_doc)
        if is_valid:
            self._write("✅ XML is valid against the selected XSD.\n")
            return

        self._write("❌ XML is NOT valid. Errors:\n\n")
        for entry in schema.error_log:
            self.last_error_entries.append(
                {
                    "line": entry.line,
                    "column": entry.column,
                    "message": entry.message,
                    "domain": entry.domain_name,
                    "type": entry.type_name,
                }
            )
            self._write(
                f"Line {entry.line}, Column {entry.column}: {entry.message} "
                f"(Domain: {entry.domain_name}, Type: {entry.type_name})\n"
            )

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

        xml_scroll_y = tk.Scrollbar(left, command=xml_editor.yview)
        xml_scroll_y.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne")
        xml_editor.configure(yscrollcommand=xml_scroll_y.set)

        tk.Label(right, text="Errors", anchor="w", font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=8, pady=(8, 2))
        error_list = tk.Listbox(right)
        error_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        tk.Label(right, text="Selected error details", anchor="w", font=("Segoe UI", 10, "bold")).pack(fill=tk.X, padx=8)
        details_panel = tk.Text(right, wrap=tk.WORD, height=8, font=("Consolas", 10))
        details_panel.pack(fill=tk.BOTH, padx=8, pady=(2, 8))
        details_panel.config(state=tk.DISABLED)

        for idx, err in enumerate(self.last_error_entries, 1):
            error_list.insert(
                tk.END,
                f"{idx}. Line {err['line']}, Col {err['column']} - {str(err['message'])[:70]}",
            )

        xml_editor.tag_configure("error_line", background="#ffe7e7")
        xml_editor.tag_remove("error_line", "1.0", tk.END)

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
            details_panel.insert(
                tk.END,
                "\n".join(
                    [
                        f"Line: {err['line']}",
                        f"Column: {err['column']}",
                        f"Domain: {err['domain']}",
                        f"Type: {err['type']}",
                        f"Message: {err['message']}",
                    ]
                ),
            )
            details_panel.config(state=tk.DISABLED)

        error_list.bind("<<ListboxSelect>>", on_select)

        buttons = tk.Frame(win)
        buttons.pack(fill=tk.X, padx=8, pady=(0, 8))

        def save_edited_xml() -> None:
            target = filedialog.asksaveasfilename(
                title="Save edited XML",
                defaultextension=".xml",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
            )
            if not target:
                return
            Path(target).write_text(xml_editor.get("1.0", tk.END), encoding="utf-8")
            messagebox.showinfo("Saved", f"Edited XML saved to:\n{target}")

        tk.Button(buttons, text="Save edited XML", command=save_edited_xml, padx=16, pady=6).pack(side=tk.RIGHT)

        if self.last_error_entries:
            error_list.selection_set(0)
            on_select()

    def _write(self, text: str) -> None:
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self._toggle_watermark()

    def _toggle_watermark(self) -> None:
        has_content = self.output.get("1.0", tk.END).strip() != ""
        if has_content:
            self.watermark.place_forget()
        else:
            self.watermark.place(relx=0.5, rely=0.5, anchor="center")


def main() -> None:
    root = tk.Tk()
    XMLXSDValidatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
