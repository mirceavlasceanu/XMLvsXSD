# XML vs XSD Validator (Windows local app)

Simple desktop app to validate an XML file against an XSD schema.

## Features

- Upload/select an **XSD** file.
- Upload/select an **XML** file.
- Click **Validate**.
- See all validation errors directly on screen.
- Click **Show details** after a failed validation to open an editable XML view with highlighted error lines and an error details panel.
- Click **Anonymize** from the main screen to open anonymization mode with save support.

## Run on Windows

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/).
2. Open **PowerShell** in this folder.
3. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

5. Start the app:

   ```powershell
   python app.py
   ```

## Optional: build an .exe

You can package it as a Windows executable with PyInstaller:

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed app.py
```

The executable will be in `dist\app.exe`.


## Versioning

The app version is displayed in the window title and under the main heading in the UI. Increment `APP_VERSION` in `app.py` whenever you make a change.


## Error details view

The **Show details** button opens a split window:
- Left side: editable XML content.
- Right side: list of validation errors.
- Clicking an error highlights its line in the XML editor and shows full error metadata in a details panel.
- You can save the edited XML from that window.


## Anonymization

The **Anonymize** window provides two options:
- **Anonymize all**: anonymizes all eligible data values in XML text/attributes while keeping XML structure intact and preserving date values.
- **Anonymize selected lines**: use line markers (☐/☑) at the beginning of lines to select multiple lines; selected lines are highlighted before anonymization.

Both modes allow saving the anonymized XML to a new file.
