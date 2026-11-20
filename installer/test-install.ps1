$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Run-Setup([string] $File, [string[]] $Arguments) {
    $process = Start-Process -FilePath $File -ArgumentList $Arguments -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "$File exited with $($process.ExitCode)"
    }
}

$root = Join-Path $env:RUNNER_TEMP 'Magpie installer verification'
$installed = Join-Path $root 'app'
$setup = (Resolve-Path 'dist/Magpie-Windows-x64-Setup.exe').Path
$oldProfile = Join-Path $env:APPDATA 'magpie-windows-amd64.exe'
$config = Join-Path $env:USERPROFILE '.config/magpie'
$recordName = 'installer-verification-' + [guid]::NewGuid().ToString('N')
$record = Join-Path $config "$recordName.json"
$browserRecord = Join-Path $oldProfile "$recordName.json"
$fixture = '{"saved":"before installation","history":["retained"]}'

New-Item -ItemType Directory -Force -Path $root, $oldProfile, $config | Out-Null
Set-Content -Path $record, $browserRecord -Value $fixture -Encoding utf8
$before = (Get-FileHash $record).Hash
$browserBefore = (Get-FileHash $browserRecord).Hash
$arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/LANG=en', '/TASKS=desktopicon', "/DIR=`"$installed`"")
Run-Setup $setup $arguments
if (!(Test-Path "$installed/magpie.exe")) { throw 'Installed program is missing' }
$startMenu = [Environment]::GetFolderPath('Programs')
$shortcutPath = Join-Path $startMenu 'Magpie.lnk'
if (!(Test-Path $shortcutPath)) { throw 'Start menu shortcut is missing' }
$shell = New-Object -ComObject WScript.Shell
if ($shell.CreateShortcut($shortcutPath).TargetPath -ne "$installed\magpie.exe") {
    throw 'Start menu shortcut points to a different program'
}
$note = Get-Content "$installed/webview-profile" -Raw
if ($note.Trim() -ne $oldProfile) { throw 'Existing WebView2 profile was not retained' }
Run-Setup $setup $arguments
if ((Get-Content "$installed/webview-profile" -Raw) -ne $note) {
    throw 'Reinstallation changed the WebView2 profile'
}
Run-Setup "$installed/unins000.exe" @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
if ((Get-FileHash $record).Hash -ne $before -or (Get-FileHash $browserRecord).Hash -ne $browserBefore) {
    throw 'Saved records changed during install, reinstall or uninstall'
}
Write-Output 'Install, shortcut, reinstall and saved-data preservation checks passed.'
Remove-Item $record, $browserRecord
