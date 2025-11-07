# Digital Signature Tool

A digital signature application for PDF documents using JSignPdf with support for smart-card certificates and USB token devices.

## Features

- **GUI Application**: Python-based Tkinter interface for easy PDF signing
- **USB Auto-Sign**: PowerShell script that automatically signs PDFs when a USB device is inserted
- **Smart Card Support**: Works with Windows certificate store and PKCS11 devices
- **Customizable Permissions**: Control PDF permissions (printing, copying, editing, etc.)
- **Visible Signatures**: Add visible signature stamps with custom images and positioning
- **Timestamp Support**: Optional TSA (Time Stamping Authority) integration

## Requirements

- Java 8 or higher (Java 17 recommended)
- JSignPdf.jar
- Python 3.x (for GUI application)
- Windows OS (for USB monitoring script)
- Smart card or USB token with digital certificate

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/PrassanthVG/Digital_signature.git
   cd Digital_signature
   ```

2. Ensure Java is installed and accessible:
   - Java should be in your PATH, or
   - Update the `DEFAULT_JAVA_CANDIDATES` in `usb_pdf_signer.py` with your Java path

3. Download JSignPdf:
   - Place `JSignPdf.jar` in the `JSignPdf` directory
   - Or update the path in the scripts to point to your JSignPdf installation

## Usage

### GUI Application

Run the Python GUI application:

```bash
python usb_pdf_signer.py
```

The application provides:
- PDF file selection
- Certificate selection from Windows certificate store
- Configurable signing options (passwords, TSA, output suffix)
- Visible signature placement and image customization
- PDF permission controls
- Real-time logging

### USB Auto-Sign Script

Run the PowerShell script to automatically sign PDFs when a USB device is inserted:

```powershell
.\usb-pdf-sign.ps1
```

**Note**: Before running, edit the script to configure:
- `$JSignJar`: Path to JSignPdf.jar
- `$KeystoreType`: "WINDOWS-MY" or "PKCS11"
- `$OwnerPwd`: Owner password for PDF permissions
- Other signing parameters as needed

The script will:
1. Monitor for USB device insertions
2. Prompt you to select a PDF file
3. Automatically sign the PDF with the configured certificate
4. Save the signed PDF with "_signed" suffix

## Configuration

### GUI Application Defaults

Edit `usb_pdf_signer.py` to customize:
- Java executable path
- JSignPdf.jar path
- Default certificate alias
- Default owner password
- Signature image path
- Signature dimensions and positioning

### PowerShell Script Configuration

Edit `usb-pdf-sign.ps1` to set:
- Keystore type (WINDOWS-MY or PKCS11)
- PKCS11 configuration file path
- Certificate alias
- Owner and user passwords
- TSA URL (optional)

## Project Structure

```
Digital_signature/
├── usb_pdf_signer.py      # Python GUI application
├── usb-pdf-sign.ps1       # PowerShell USB monitoring script
├── JSignPdf/              # JSignPdf tool directory
│   └── JSignPdf.jar
├── temurin-jre/           # Java Runtime Environment
└── README.md              # This file
```

## License

This project uses JSignPdf, which is licensed under LGPL 2.1 and MPL 2.0. See the `JSignPdf/licenses/` directory for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

PrassanthVG

## Repository

https://github.com/PrassanthVG/Digital_signature.git

