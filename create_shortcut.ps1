$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\AutoPilot OS V2.lnk")
$Shortcut.TargetPath = "D:\Projects\AutoPilot_OS_v2\os_env\Scripts\python.exe"
$Shortcut.Arguments = "D:\Projects\AutoPilot_OS_v2\AutoPilot_GUI.py"
$Shortcut.WorkingDirectory = "D:\Projects\AutoPilot_OS_v2"
$Shortcut.Description = "AutoPilot OS V2 - Control Center"
$Shortcut.IconLocation = "D:\Projects\AutoPilot_OS_v2\os_env\Scripts\python.exe, 0"
$Shortcut.Save()
Write-Host "Shortcut created on Desktop: AutoPilot OS V2.lnk"