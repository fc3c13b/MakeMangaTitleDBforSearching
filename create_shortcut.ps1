$shell = New-Object -ComObject WScript.Shell
$desktop = "$env:USERPROFILE\Desktop"
$path = "$desktop\MakeMangaTitleDBforSearching Progress Monitor.lnk"

$shortcut = $shell.CreateShortcut($path)
$shortcut.TargetPath = "C:\source\repos\MakeMangaTitleDBforSearching\.venv\Scripts\python.exe"
$shortcut.Arguments = """C:\source\repos\MakeMangaTitleDBforSearching\progress_monitor.py""""
$shortcut.WorkingDirectory = "C:\source\repos\MakeMangaTitleDBforSearching"
$shortcut.Description = "MakeMangaTitleDBforSearching - Progress Monitor"
$shortcut.IconLocation = "shell32.dll,13"
$shortcut.Save()

Write-Output "Shortcut created: $path"
