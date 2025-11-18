# AI Stack - Vault File Watcher (PowerShell/Windows)
# Monitors vault directory for changes and triggers re-embedding

param(
    [string]$VaultPath = "C:\ai_stack\vault",
    [string]$WebhookUrl = "http://localhost:5678/webhook/reembed-file",
    [int]$DebounceSeconds = 5
)

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  AI Stack - Vault File Watcher (PowerShell)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Watching: $VaultPath" -ForegroundColor White
Write-Host "Webhook: $WebhookUrl" -ForegroundColor White
Write-Host "Debounce: ${DebounceSeconds}s" -ForegroundColor White
Write-Host ""

# Check if vault directory exists
if (-not (Test-Path $VaultPath)) {
    Write-Host "Error: Vault directory not found: $VaultPath" -ForegroundColor Red
    exit 1
}

# Track last processed time for debouncing
$script:lastProcessed = @{}

function Get-FileHashString {
    param([string]$FilePath)

    if (Test-Path $FilePath) {
        $hash = Get-FileHash -Path $FilePath -Algorithm SHA256
        return $hash.Hash.ToLower()
    }
    return $null
}

function Process-File {
    param(
        [string]$FilePath,
        [string]$ChangeType
    )

    # Skip hidden files and temp files
    $fileName = [System.IO.Path]::GetFileName($FilePath)
    if ($fileName.StartsWith(".") -or $fileName.EndsWith("~")) {
        return
    }

    # Only process markdown files
    if (-not $FilePath.EndsWith(".md")) {
        return
    }

    # Debounce: skip if processed recently
    $currentTime = Get-Date
    if ($script:lastProcessed.ContainsKey($FilePath)) {
        $lastTime = $script:lastProcessed[$FilePath]
        $timeDiff = ($currentTime - $lastTime).TotalSeconds
        if ($timeDiff -lt $DebounceSeconds) {
            return
        }
    }
    $script:lastProcessed[$FilePath] = $currentTime

    # Get file info
    $relativePath = $FilePath.Replace($VaultPath, "").TrimStart('\', '/')
    $fileHash = Get-FileHashString -FilePath $FilePath
    $fileSize = (Get-Item $FilePath -ErrorAction SilentlyContinue).Length

    Write-Host "📝 Processing: $relativePath" -ForegroundColor Green
    Write-Host "   Event: $ChangeType | Size: $fileSize bytes" -ForegroundColor Gray

    # Prepare webhook payload
    $payload = @{
        file_path = $FilePath
        relative_path = $relativePath
        file_hash = $fileHash
        file_size = $fileSize
        event = $ChangeType
        timestamp = (Get-Date -Format "o")
    } | ConvertTo-Json

    # Trigger webhook
    try {
        $response = Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 30
        Write-Host "   ✓ Re-embedding triggered" -ForegroundColor Green
    }
    catch {
        Write-Host "   ⚠ Webhook failed: $_" -ForegroundColor Yellow
    }

    Write-Host ""
}

# Create FileSystemWatcher
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $VaultPath
$watcher.Filter = "*.md"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

# Define event actions
$onChange = {
    $path = $Event.SourceEventArgs.FullPath
    $changeType = $Event.SourceEventArgs.ChangeType
    Process-File -FilePath $path -ChangeType $changeType
}

$onCreate = {
    $path = $Event.SourceEventArgs.FullPath
    Process-File -FilePath $path -ChangeType "Created"
}

$onDelete = {
    $path = $Event.SourceEventArgs.FullPath
    $relativePath = $path.Replace($VaultPath, "").TrimStart('\', '/')
    Write-Host "🗑 Deleted: $relativePath" -ForegroundColor Yellow
    Write-Host ""
}

$onRename = {
    $path = $Event.SourceEventArgs.FullPath
    Process-File -FilePath $path -ChangeType "Renamed"
}

# Register events
$handlers = @()
$handlers += Register-ObjectEvent -InputObject $watcher -EventName "Changed" -Action $onChange
$handlers += Register-ObjectEvent -InputObject $watcher -EventName "Created" -Action $onCreate
$handlers += Register-ObjectEvent -InputObject $watcher -EventName "Deleted" -Action $onDelete
$handlers += Register-ObjectEvent -InputObject $watcher -EventName "Renamed" -Action $onRename

Write-Host "👀 Watching for changes..." -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    # Cleanup on exit
    Write-Host ""
    Write-Host "Stopping watcher..." -ForegroundColor Yellow

    foreach ($handler in $handlers) {
        Unregister-Event -SourceIdentifier $handler.Name -ErrorAction SilentlyContinue
    }

    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()

    Write-Host "✓ Stopped" -ForegroundColor Green
}
