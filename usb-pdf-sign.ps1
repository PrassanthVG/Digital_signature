# usb-pdf-sign.ps1 — PDF only: on USB insert, pick a PDF, sign it, and disable copy
# Pre-req: Java 8+, JSignPdf.jar, and your token driver installed

Add-Type -AssemblyName System.Windows.Forms

# ====== EDIT THESE VALUES ======
$JSignJar     = "C:\tools\JSignPdf\JSignPdf.jar"   # path to JSignPdf.jar
$KeystoreType = "WINDOWS-MY"                       # "WINDOWS-MY" or "PKCS11"
$Pkcs11Cfg    = "C:\tools\JSignPdf\pkcs11.cfg"     # required when using PKCS11
$Pkcs11Pin    = $env:USB_SIGN_PIN                  # set as env var for PKCS11
$OwnerPwd     = "Owner#Strong#987"                 # owner (permissions) password
$UserPwd      = ""                                 # optional open password
$CertAlias    = ""                                 # optional substring to select a cert
$TsaUrl       = ""                                 # optional TSA URL for timestamp
# =================================

function Invoke-JSign([string]$pdfIn) {
    $outDir = [IO.Path]::GetDirectoryName($pdfIn)
    $args   = @("-jar", $JSignJar)

    switch ($KeystoreType) {
        "WINDOWS-MY" {
            $args += @("-kst","WINDOWS-MY")
        }
        "PKCS11" {
            $args += @("-kst","PKCS11","-ksf",$Pkcs11Cfg)
            if ($Pkcs11Pin) { $args += @("-ksp",$Pkcs11Pin) }
        }
        default {
            throw "KeystoreType must be WINDOWS-MY or PKCS11"
        }
    }

    if ($CertAlias) { $args += @("-ka", $CertAlias) }

    # One-pass: certify (no changes) + set permissions (disable copy)
    $args += @(
        "-cl","CERTIFIED_NO_CHANGES_ALLOWED",
        "-pe","PASSWORD",
        "--disable-copy",
        "-opwd",$OwnerPwd,
        "-os","_signed","-d",$outDir
    )

    if ($UserPwd) { $args += @("-upwd",$UserPwd) }
    if ($TsaUrl) { $args += @("-ts",$TsaUrl) }

    $args += $pdfIn
    Start-Process -FilePath "java" -ArgumentList $args -NoNewWindow -Wait
}

function Select-And-Sign {
    $ofd = New-Object System.Windows.Forms.OpenFileDialog
    $ofd.Filter = "PDF files|*.pdf"
    $ofd.Multiselect = $false

    if ($ofd.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { return }

    $pdf = $ofd.FileName
    Invoke-JSign $pdf

    $out = [IO.Path]::Combine(
        [IO.Path]::GetDirectoryName($pdf),
        [IO.Path]::GetFileNameWithoutExtension($pdf) + "_signed.pdf"
    )

    [Windows.Forms.MessageBox]::Show("Signed: `n$out") | Out-Null
}

Register-WmiEvent -Class Win32_DeviceChangeEvent -SourceIdentifier "UsbWatch" -Action {
    try {
        $etype = $Event.SourceEventArgs.NewEvent.EventType
        if ($etype -eq 2) { Select-And-Sign }
    } catch {
        Write-Warning $_
    }
} | Out-Null

Write-Host "Watching for USB insert... (leave this window open)  Press Ctrl+C to stop."
while ($true) { Start-Sleep -Seconds 2 }
