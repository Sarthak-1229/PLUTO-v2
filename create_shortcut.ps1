$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\PLUTO v2.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\start_pluto.bat"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.Description = "Launch PLUTO v2 AI Agent"
# Try to use a built-in icon or leave default
$Shortcut.IconLocation = "%SystemRoot%\System32\SHELL32.dll,22" 
$Shortcut.Save()
Write-Host "Shortcut created at $DesktopPath\PLUTO v2.lnk"
