$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\PLUTO v2.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\start_pluto.bat"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.Description = "PLUTO v2 - Local AI Research Assistant"
$Shortcut.IconLocation = "$PSScriptRoot\logo3.png,0"
$Shortcut.Save()
Write-Host "Desktop shortcut created: PLUTO v2.lnk"
