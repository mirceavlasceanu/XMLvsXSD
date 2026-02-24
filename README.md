# XML vs XSD Validator (Windows local app)

Simple desktop app to validate an XML file against an XSD schema.

## Features

- Upload/select an **XSD** file.
- Upload/select an **XML** file.
- Click **Validate**.
- See all validation errors directly on screen.

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
