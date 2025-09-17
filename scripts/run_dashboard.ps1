Param(
    [switch]$Rebuild
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Telco Retention Dashboard Launcher (PowerShell)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check .env
if (-not (Test-Path .env)) {
    Write-Host "ERROR: .env file not found." -ForegroundColor Red
    Write-Host "Create a .env file with (example):" -ForegroundColor Yellow
    Write-Host "AZURE_OPENAI_API_KEY=your_key"
    Write-Host "AZURE_OPENAI_ENDPOINT=your_endpoint"
    Write-Host "AZURE_OPENAI_MODEL_NAME=your_model"
    exit 1
}

# Check Docker
try {
    docker info > $null 2>&1
} catch {
    Write-Host "ERROR: Docker is not running. Start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Prefer 'docker compose' if available, else fallback
$composeCmd = 'docker compose'
if (-not (docker compose version > $null 2>&1)) {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $composeCmd = 'docker-compose'
    }
}

Write-Host "Stopping any existing containers..." -ForegroundColor DarkGray
& $composeCmd down

$upArgs = 'up','-d'
if ($Rebuild) { $upArgs = @('up','--build','-d') }

Write-Host "Starting services..." -ForegroundColor DarkGray
& $composeCmd @upArgs
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR starting services" -ForegroundColor Red; exit 1 }

Write-Host "Waiting for services to initialize..." -ForegroundColor DarkGray
Start-Sleep -Seconds 10

# Check backend health
Write-Host "Checking backend health..." -ForegroundColor DarkGray
$backendReady = $false
for ($i = 1; $i -le 5; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/api/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Backend is responding!" -ForegroundColor Green
            $backendReady = $true
            break
        }
    } catch {
        Write-Host "   Attempt $i/5... waiting..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 3
    }
}

# Check containers state
$psOut = & $composeCmd ps
if ($psOut -match 'Up') {
    Write-Host "✅ Services started successfully!" -ForegroundColor Green
    Write-Host "🌐 Dashboard: http://localhost:8050" -ForegroundColor Green
    Write-Host "🔧 API: http://localhost:8001/api/health" -ForegroundColor Green
} else {
    Write-Host "⚠️  Services may have issues, but containers are running" -ForegroundColor Yellow
    Write-Host "🌐 Try opening: http://localhost:8050" -ForegroundColor Yellow
}

# Open browser
try { Start-Process "http://localhost:8050" } catch {}

Write-Host "View logs: $composeCmd logs -f" -ForegroundColor Yellow
Write-Host "Stop: $composeCmd down" -ForegroundColor Yellow
