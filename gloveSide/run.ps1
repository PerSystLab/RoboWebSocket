# Get user's Desktop path
$desktopPath = [Environment]::GetFolderPath("Desktop")

# Construct the full path of the project directory
$projectPath = Join-Path $desktopPath "graduateproject"

# Navigate to the specified directory
Set-Location $projectPath

# Find Chrome windows that contain 'client1.html'
$chromeProcesses = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*client1.html*" }

# Close each found Chrome process
foreach ($process in $chromeProcesses) {
    # Attempt to close the main window
    $process.CloseMainWindow()
    
    # Wait briefly for the process to close
    Start-Sleep -Seconds 2
    
    # If the process is still running, forcefully kill it
    if (!$process.HasExited) {
        $process.Kill()
    }
}

# Open the new HTML file in Chrome
Start-Process "chrome.exe" (Join-Path $projectPath "client1blu.html")

# Yeni terminal penceresinde websocket sunucusunu yönetmek için bir komut oluşturun
$command = "while (`$true) { try { ssh root@kyncd -t 'cd /home/kync/Desktop/scripts; node websocket-server.js'; Write-Host 'Websocket sunucusu kapandı. Yeniden başlatılıyor...' -ForegroundColor Yellow; Start-Sleep -Seconds 5 } catch { Write-Host 'Hata oluştu: $($_.Exception.Message)' -ForegroundColor Red; Start-Sleep -Seconds 5 } }"

# Yeni PowerShell penceresi açarak komutu çalıştır
Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-Command",
    $command
)

# Wait 1 second
Start-Sleep -Seconds 1

# Make the second SSH connection in a new terminal window, navigate to the directory and run 'node client2.js'
Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-Command",
    "ssh root@kyncd -t 'cd /home/kync/Desktop/scripts; node client2.js; exec bash'"
)

