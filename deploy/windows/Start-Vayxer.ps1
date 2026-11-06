[CmdletBinding()]
param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root

function Test-Engine {
    try {
        docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Instala Docker Desktop para Windows, ábrelo y vuelve a ejecutar Vayxer.'
    }
    if (-not (Test-Engine)) {
        Write-Host 'Iniciando Docker Desktop...'
        $started = $false
        try {
            docker desktop start --timeout 120 2>$null | Out-Null
            $started = $LASTEXITCODE -eq 0
        } catch {
            # Versiones anteriores pueden carecer del subcomando desktop.
        }
        if (-not $started) {
            $desktop = @(
                (Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/Docker Desktop.exe'),
                (Join-Path $env:ProgramFiles 'Docker/Docker/Docker Desktop.exe')
            ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
            if ($desktop) { Start-Process -FilePath $desktop -WindowStyle Hidden }
        }
        $deadline = [DateTime]::UtcNow.AddSeconds(90)
        while (-not (Test-Engine)) {
            if ([DateTime]::UtcNow -ge $deadline) {
                throw 'Abre Docker Desktop, verifica que el motor de contenedores Linux esté listo y vuelve a intentar.'
            }
            Start-Sleep -Seconds 2
        }
    }
    docker compose version --short | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Actualiza Docker Desktop para instalar el complemento Docker Compose.' }

    if (-not (Test-Path -LiteralPath '.env')) {
        Write-Host 'Preparando la configuración local...'
        $py = Get-Command py.exe -ErrorAction SilentlyContinue
        $python = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($py) {
            & $py.Source -3 deploy/setup.py
        } elseif ($python -and $python.Source -notlike '*\WindowsApps\*') {
            & $python.Source deploy/setup.py
        } else {
            throw 'Instala Python 3.11 o posterior y vuelve a ejecutar Vayxer. Se usa para crear el archivo .env en el primer inicio.'
        }
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar .env. Comprueba tu instalación de Python y los permisos de la carpeta.' }
    }

    Write-Host 'Preparando Vayxer. El primer arranque puede tardar unos minutos...'
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Revisa la configuración local con docker compose config --quiet.' }
    docker compose up -d --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) {
        docker compose ps -a
        throw 'Revisa Docker Desktop y los registros con docker compose logs --tail 40. Si el puerto está ocupado, cambia PORT en .env.'
    }

    $ports = @(docker compose port gateway 80 2>$null)
    $portExit = $LASTEXITCODE
    $binding = ([string]($ports | Select-Object -First 1)).Trim()
    if ($portExit -ne 0 -or $binding -notmatch '^127\.0\.0\.1:(\d+)$') {
        throw 'No se encontró el puerto HTTP local. Comprueba el servicio gateway y la variable PORT de .env.'
    }
    $url = "http://127.0.0.1:$($Matches[1])"
    $deadline = [DateTime]::UtcNow.AddSeconds(35)
    $ready = $false
    do {
        try {
            $response = Invoke-WebRequest -Uri "$url/api/ready" -UseBasicParsing -TimeoutSec 3
            $health = $response.Content | ConvertFrom-Json
            if ($response.StatusCode -eq 200 -and $health.status -eq 'ready') {
                $ready = $true
                break
            }
        } catch {
            # El gateway puede estar resolviendo los nodos recién iniciados.
        }
        Start-Sleep -Seconds 1
    } while ([DateTime]::UtcNow -lt $deadline)
    if (-not $ready) {
        throw 'La API no confirmó disponibilidad. Revisa docker compose ps y docker compose logs --tail 40.'
    }
    Write-Host "Vayxer listo en $url"
    if (-not $NoBrowser) { Start-Process $url }
    exit 0
} catch {
    Write-Host "Vayxer: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
