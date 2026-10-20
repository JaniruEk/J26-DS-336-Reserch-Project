<#
.SYNOPSIS
  Start the team app (chat, Pipeline Explorer, dashboard) on this machine, with the checks that usually go wrong.

.EXAMPLE
  .\scripts\start_app.ps1                      # this machine only; picks the SQL model by itself
  .\scripts\start_app.ps1 -Restart             # first stop an old copy that is still holding the port
  .\scripts\start_app.ps1 -Share               # let teammates on the same network use it (prints address + admin token)
  .\scripts\start_app.ps1 -Generator ollama:phi3
#>
param(
  [string]$Generator = "",   # adaptive_qwen | ollama:<model>; empty = adaptive_qwen if this PC has a working NVIDIA setup, else ollama:phi3
  [string]$Gate = "",        # kd_multitask | word_match; empty = kd_multitask if Agent 2's files and the GPU packages are here
  [int]$Port = 8765,
  [switch]$Restart,
  [switch]$Share
)
Set-Location (Split-Path $PSScriptRoot -Parent)

# 1. Port: an old copy left running silently blocks a new one
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
  if ($Restart) {
    $busy | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
    Start-Sleep -Seconds 2
    Write-Host "Stopped the old copy on port $Port."
  } else {
    Write-Host "Port $Port is already in use (process $($busy[0].OwningProcess)). Run with -Restart to stop it, or pick another port with -Port 8000." -ForegroundColor Yellow
    exit 1
  }
}

# 2. SQL model
if (-not $Generator) {
  python -c "import sys, torch, transformers, bitsandbytes; sys.exit(0 if torch.cuda.is_available() else 1)" *> $null
  if ($LASTEXITCODE -eq 0) { $Generator = "adaptive_qwen" } else { $Generator = "ollama:phi3" }
}
$env:J26_GENERATOR = $Generator
Write-Host "SQL model: $Generator"
if ($Generator -like "ollama:*") {
  try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://localhost:11434/api/tags | Out-Null }
  catch { Write-Host "  Ollama is not running, so the chat can't write SQL yet: start Ollama (or run 'ollama serve'). The Explorer's retrieval tab works without it." -ForegroundColor Yellow }
} elseif ($Generator -eq "adaptive_qwen") {
  Write-Host "  Building Agent 4's mixed INT4/INT8 model takes about 2 minutes; the first question waits for it."
}

# 2b. Question gate: Agent 2's distilled student when her files and the GPU packages (incl. peft) are here
if (-not $Gate) {
  $Gate = "word_match"
  if (Test-Path "MultiTask_Research/student_1_5b_kd_multitask/final_adapter/adapter_model.safetensors") {
    python -c "import sys, torch, peft; sys.exit(0 if torch.cuda.is_available() else 1)" *> $null
    if ($LASTEXITCODE -eq 0) { $Gate = "kd_multitask" }
  }
}
$env:J26_GATE = $Gate
if ($Gate -eq "kd_multitask") { Write-Host "Question gate: Agent 2's distilled Qwen2.5-1.5B student (plus Agent 1's word check)" }
else { Write-Host "Question gate: Agent 1's word check (Agent 2's model needs MultiTask_Research/ and the GPU packages)" }

# 3. PostgreSQL copies of Chinook and Northwind (optional: needs Docker Desktop running and the j26-postgres container)
$pg = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker start j26-postgres *> $null
  $pg = ($LASTEXITCODE -eq 0)
}
if ($pg -and -not $env:J26_DATABASES) {
  $env:J26_DATABASES = '{"chinook_postgres": "postgresql+psycopg://ro_user:ro_pass@127.0.0.1:55432/chinook", "northwind_postgres": "postgresql+psycopg://ro_user:ro_pass@127.0.0.1:55432/northwind"}'
  Write-Host "PostgreSQL databases: chinook_postgres, northwind_postgres"
} elseif (-not $pg) {
  Write-Host "PostgreSQL databases skipped: Docker Desktop is not running, or there is no j26-postgres container. Everything else works."
}

# 4. This machine only, or the local network
$bind = "127.0.0.1"
if ($Share) {
  $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object -First 1).IPAddress
  if (-not $env:J26_ADMIN_TOKEN) { $env:J26_ADMIN_TOKEN = [guid]::NewGuid().ToString("N").Substring(0, 16) }
  $env:J26_ALLOWED_HOSTS = $ip
  $bind = "0.0.0.0"
  Write-Host ""
  Write-Host "Teammates open:  http://${ip}:$Port/chat   (wrong address? 'ipconfig' lists the others)"
  Write-Host "Admin token for adding databases from their machine: $($env:J26_ADMIN_TOKEN)"
  Write-Host "Private networks only: the app has no login yet. If Windows Firewall asks, allow Python on Private networks." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Chat:      http://localhost:$Port/chat"
Write-Host "Explorer:  http://localhost:$Port/"
Write-Host "Dashboard: http://localhost:$Port/dashboard"
Write-Host "Stop with Ctrl+C."
Write-Host ""
python -m uvicorn harness.app:app --host $bind --port $Port
