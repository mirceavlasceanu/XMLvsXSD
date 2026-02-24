import tkinter as tk
from copy import deepcopy
from pathlib import Path
from tkinter import filedialog, messagebox

from lxml import etree

APP_VERSION = "1.1.0"
XSD_NS = "http://www.w3.org/2001/XMLSchema"


class XMLXSDValidatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"XML vs XSD Validator v{APP_VERSION}")
        self.root.geometry("900x600")

        self.xsd_path: Path | None = None
        self.xml_path: Path | None = None

        self.last_schema: etree.XMLSchema | None = None
        self.last_xsd_doc: etree._ElementTree | None = None
        self.last_xml_doc: etree._ElementTree | None = None

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

        self.fix_button = tk.Button(
            controls,
            text="Fix",
            command=self.fix_xml,
            state=tk.DISABLED,
            padx=16,
            pady=6,
        )
        self.fix_button.pack(side=tk.LEFT, padx=(8, 0))

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
        self.fix_button.config(state=tk.DISABLED)

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

        self.last_xsd_doc = xsd_doc
        self.last_schema = schema
        self.last_xml_doc = xml_doc

        if schema.validate(xml_doc):
            self._write("✅ XML is valid against the selected XSD.\n")
            return

        self._write("❌ XML is NOT valid. Errors:\n\n")
        for entry in schema.error_log:
            self._write(
                f"Line {entry.line}, Column {entry.column}: {entry.message} "
                f"(Domain: {entry.domain_name}, Type: {entry.type_name})\n"
            )

        self.fix_button.config(state=tk.NORMAL)

    def fix_xml(self) -> None:
        if not self.last_xsd_doc or not self.last_xml_doc or not self.last_schema:
            messagebox.showwarning("No validation context", "Please validate an XML/XSD pair first.")
            return

        try:
            fixed_doc = self._auto_fix_xml_structure(self.last_xsd_doc, self.last_xml_doc)
            fixed_text = etree.tostring(
                fixed_doc,
                pretty_print=True,
                encoding="utf-8",
                xml_declaration=True,
            ).decode("utf-8")
        except Exception as exc:  # best-effort fixer
            messagebox.showerror("Fix failed", f"Could not auto-fix XML:\n{exc}")
            return

        is_valid = self.last_schema.validate(fixed_doc)
        status = "✅ Auto-fixed XML validates against XSD." if is_valid else "⚠️ Auto-fix applied, but XML is still not fully valid."
        self._show_fixed_xml_window(fixed_text, status)

    def _auto_fix_xml_structure(
        self, xsd_doc: etree._ElementTree, xml_doc: etree._ElementTree
    ) -> etree._ElementTree:
        source_root = xml_doc.getroot()
        fixed_root = etree.Element(source_root.tag, nsmap=source_root.nsmap)
        fixed_root.attrib.update(source_root.attrib)

        root_def = self._find_xsd_root_definition(xsd_doc.getroot(), self._local_name(source_root.tag))
        expected_children = self._extract_expected_child_elements(root_def)

        used = set()
        for child_name, min_occurs in expected_children:
            matches = [
                (index, child)
                for index, child in enumerate(source_root)
                if index not in used and self._local_name(child.tag) == child_name
            ]

            if matches:
                for index, matched in matches:
                    fixed_root.append(deepcopy(matched))
                    used.add(index)
                continue

            for _ in range(min_occurs):
                fixed_root.append(self._new_child_with_namespace(source_root, child_name))

        for index, child in enumerate(source_root):
            if index not in used:
                fixed_root.append(deepcopy(child))

        return etree.ElementTree(fixed_root)

    def _find_xsd_root_definition(self, xsd_root: etree._Element, root_name: str) -> etree._Element:
        path = f"./{{{XSD_NS}}}element[@name='{root_name}']"
        root_def = xsd_root.find(path)
        if root_def is None:
            raise ValueError(f"Could not find root element '{root_name}' in XSD.")
        return root_def

    def _extract_expected_child_elements(self, root_def: etree._Element) -> list[tuple[str, int]]:
        expected: list[tuple[str, int]] = []
        sequence = root_def.find(f"./{{{XSD_NS}}}complexType/{{{XSD_NS}}}sequence")
        if sequence is None:
            return expected

        for element in sequence.findall(f"./{{{XSD_NS}}}element"):
            child_name = element.get("name")
            if not child_name:
                continue
            min_occurs = int(element.get("minOccurs", "1"))
            expected.append((child_name, min_occurs))
        return expected

    def _new_child_with_namespace(self, parent: etree._Element, child_name: str) -> etree._Element:
        if parent.tag.startswith("{"):
            namespace = parent.tag.split("}", 1)[0][1:]
            tag = f"{{{namespace}}}{child_name}"
        else:
            tag = child_name
        return etree.Element(tag)

    def _local_name(self, tag: str) -> str:
        return tag.split("}", 1)[-1]

    def _show_fixed_xml_window(self, fixed_xml: str, status: str) -> None:
        win = tk.Toplevel(self.root)
        win.title("Fixed XML (ready to save)")
        win.geometry("900x600")

        tk.Label(win, text=status, anchor="w").pack(fill=tk.X, padx=12, pady=(12, 6))

        text = tk.Text(win, wrap=tk.NONE, font=("Consolas", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        text.insert("1.0", fixed_xml)

        button_frame = tk.Frame(win)
        button_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        def save_fixed_xml() -> None:
            target = filedialog.asksaveasfilename(
                title="Save fixed XML",
                defaultextension=".xml",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
            )
            if not target:
                return
            Path(target).write_text(text.get("1.0", tk.END), encoding="utf-8")
            messagebox.showinfo("Saved", f"Fixed XML saved to:\n{target}")

        tk.Button(button_frame, text="Save", command=save_fixed_xml, padx=16, pady=6).pack(side=tk.RIGHT)

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
