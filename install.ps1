param(
    [string]$InstallDir = "$env:LOCALAPPDATA\VoiceChanger"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$PythonVersion = "3.12"
$VbCableUrl = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"
$SourceDir = $PSScriptRoot

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Find-Python {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        try {
            $ErrorActionPreference = "Continue"
            $path = & py "-$PythonVersion" -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $path) { return ([string]$path).Trim() }
        } catch {
        }
    }
    $userInstall = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    if (Test-Path $userInstall) { return $userInstall }
    return $null
}

function Install-Python {
    $python = Find-Python
    if ($python) {
        Write-Host "Python $PythonVersion déjà présent : $python"
        return $python
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget est introuvable. Installe Python $PythonVersion depuis https://www.python.org/downloads/ puis relance ce script."
    }
    winget install --exact --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements | Out-Host
    $python = Find-Python
    if (-not $python) { throw "Python $PythonVersion n'a pas pu être installé." }
    return $python
}

function Test-VbCable {
    $devices = Get-CimInstance Win32_SoundDevice | Where-Object { $_.Name -like "*VB-Audio*" }
    return [bool]$devices
}

function Install-VbCable {
    if (Test-VbCable) {
        Write-Host "VB-Audio Virtual Cable déjà installé."
        return $false
    }
    $archive = Join-Path $env:TEMP "VBCABLE_Driver_Pack.zip"
    $extracted = Join-Path $env:TEMP "VBCABLE_Driver_Pack"
    Invoke-WebRequest -Uri $VbCableUrl -OutFile $archive -UseBasicParsing
    Expand-Archive -Path $archive -DestinationPath $extracted -Force
    $setupName = if ([Environment]::Is64BitOperatingSystem) { "VBCABLE_Setup_x64.exe" } else { "VBCABLE_Setup.exe" }
    Write-Host "Une fenêtre d'administration va s'ouvrir : accepte, puis clique sur « Install Driver »."
    Start-Process -FilePath (Join-Path $extracted $setupName) -Verb RunAs -Wait
    return $true
}

function Copy-AppFiles {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Copy-Item -Path (Join-Path $SourceDir "voicechanger") -Destination $InstallDir -Recurse -Force
    Copy-Item -Path (Join-Path $SourceDir "requirements.txt") -Destination $InstallDir -Force
    Copy-Item -Path (Join-Path $SourceDir "presets.json") -Destination (Join-Path $InstallDir "presets.default.json") -Force
    $userPresets = Join-Path $InstallDir "presets.json"
    if (Test-Path $userPresets) {
        Write-Host "presets.json existant conservé (les presets d'origine sont dans presets.default.json)."
    } else {
        Copy-Item -Path (Join-Path $SourceDir "presets.json") -Destination $userPresets
    }
}

function Install-Dependencies($Python) {
    $venv = Join-Path $InstallDir ".venv"
    if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
        & $Python -m venv $venv | Out-Host
    }
    $venvPython = Join-Path $venv "Scripts\python.exe"
    & $venvPython -m pip install --upgrade pip --quiet | Out-Host
    & $venvPython -m pip install -r (Join-Path $InstallDir "requirements.txt") --quiet | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "L'installation des dépendances Python a échoué." }
}

function New-Shortcuts {
    $shell = New-Object -ComObject WScript.Shell
    $targets = @(
        [Environment]::GetFolderPath("Desktop"),
        (Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs")
    )
    foreach ($folder in $targets) {
        $shortcut = $shell.CreateShortcut((Join-Path $folder "Voice Changer.lnk"))
        $shortcut.TargetPath = Join-Path $InstallDir ".venv\Scripts\pythonw.exe"
        $shortcut.Arguments = "-m voicechanger"
        $shortcut.WorkingDirectory = $InstallDir
        $shortcut.IconLocation = "$env:SystemRoot\System32\SndVol.exe,0"
        $shortcut.Save()
    }
}

Write-Step "1/5 Python $PythonVersion"
$python = Install-Python

Write-Step "2/5 Câble audio virtuel (VB-Audio Virtual Cable)"
$rebootNeeded = Install-VbCable

Write-Step "3/5 Copie de l'application dans $InstallDir"
Copy-AppFiles

Write-Step "4/5 Dépendances Python (numpy, sounddevice, pedalboard, pynput)"
Install-Dependencies $python

Write-Step "5/5 Raccourcis Bureau et menu Démarrer"
New-Shortcuts

Write-Host ""
Write-Host "Installation terminée." -ForegroundColor Green
if ($rebootNeeded) {
    Write-Host "Redémarre Windows pour activer le câble virtuel avant le premier lancement." -ForegroundColor Yellow
}
Write-Host "Dans Discord > Paramètres > Voix et vidéo :"
Write-Host "  - Périphérique d'entrée : CABLE Output (VB-Audio Virtual Cable)"
Write-Host "  - Désactive la suppression de bruit (Krisp), l'annulation d'écho et le contrôle automatique du gain"
