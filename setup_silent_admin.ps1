if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$TaskName = "JarvisSilentAdmin"
$TaskName = "JarvisSilentAdmin"
$VenvPath = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (!(Test-Path $VenvPath)) {
    $VenvPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
}

if (Test-Path $VenvPath) {
    $PythonPath = $VenvPath
}
else {
    $PythonPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if (!$PythonPath) {
        $PythonPath = "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    }
}
$JarvisPath = Join-Path $PSScriptRoot "jarvis.py"
$WorkingDirectory = $PSScriptRoot

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$JarvisPath`"" -WorkingDirectory $WorkingDirectory
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId "$($env:USERDOMAIN)\$($env:USERNAME)" -LogonType Interactive -RunLevel Highest

Write-Host "Configurando tarefa agendada: $TaskName"
Register-ScheduledTask -Action $Action -Trigger $Trigger -Principal $Principal -TaskName $TaskName -Force

Write-Host "Sucesso! O JARVIS agora iniciará como Administrador sem confirmação de UAC ao fazer logon."
