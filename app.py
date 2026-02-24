import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

from lxml import etree


class XMLXSDValidatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("XML vs XSD Validator")
        self.root.geometry("900x600")

        self.xsd_path: Path | None = None
        self.xml_path: Path | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=12, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(
            container,
            text="Validate XML against XSD",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(anchor="w", pady=(0, 12))

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

        tk.Button(
            container,
            text="Validate",
            command=self.validate,
            bg="#0d6efd",
            fg="white",
            padx=16,
            pady=6,
        ).pack(anchor="w", pady=12)

        tk.Label(container, text="Validation output:", anchor="w").pack(anchor="w")

        output_frame = tk.Frame(container)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.watermark = tk.Label(
            output_frame,
            text="Mircea",
            font=("Segoe UI", 56, "bold"),
            fg="#d8d8d8",
        )
        self.watermark.place(relx=0.5, rely=0.5, anchor="center")

        self.output = tk.Text(output_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.bind("<KeyRelease>", self._toggle_watermark)
        self.output.bind("<<Modified>>", self._toggle_watermark)

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
            return

        is_valid = schema.validate(xml_doc)
        if is_valid:
            self._write("✅ XML is valid against the selected XSD.\n")
            return

        self._write("❌ XML is NOT valid. Errors:\n\n")
        for entry in schema.error_log:
            self._write(
                f"Line {entry.line}, Column {entry.column}: {entry.message} "
                f"(Domain: {entry.domain_name}, Type: {entry.type_name})\n"
            )

    def _write(self, text: str) -> None:
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self._toggle_watermark()

    def _toggle_watermark(self, _event=None) -> None:
        has_content = self.output.get("1.0", tk.END).strip() != ""
        if has_content:
            self.watermark.place_forget()
        else:
            self.watermark.place(relx=0.5, rely=0.5, anchor="center")


def main() -> None:
    root = tk.Tk()
    app = XMLXSDValidatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
