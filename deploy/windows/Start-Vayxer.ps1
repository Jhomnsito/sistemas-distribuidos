[CmdletBinding()]
param([switch]$NoBrowser, [switch]$RenewCertificate)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
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
        $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $values = foreach ($name in @('POSTGRES_PASSWORD','APP_PASSWORD','REPL_PASSWORD','DATA_KEY')) {
                $bytes = New-Object byte[] 32
                $rng.GetBytes($bytes)
                $value = [Convert]::ToBase64String($bytes).Replace('+','-').Replace('/','_')
                "$name=$value"
            }
            $stream = [IO.File]::Open((Join-Path $root '.env'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
            try {
                $writer = New-Object IO.StreamWriter($stream,[Text.UTF8Encoding]::new($false))
                try { $writer.WriteLine(($values -join "`n")) } finally { $writer.Dispose() }
            } finally { $stream.Dispose() }
        } finally { $rng.Dispose() }
    }

    $tls = Join-Path $root 'local-tls'
    $cert = Join-Path $tls 'cert.pem'
    $key = Join-Path $tls 'key.pem'
    if (-not (Test-Path -LiteralPath $cert) -and -not (Test-Path -LiteralPath $key)) {
        Write-Host 'Preparando un certificado HTTPS para este equipo...'
        New-Item -ItemType Directory -Path $tls -Force | Out-Null
        docker compose run --rm --build --no-deps -T --user 0 --volume "${tls}:/tls" monitor python tls_setup.py
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar el certificado HTTPS. Revisa Docker Desktop.' }
    }
    if (-not (Test-Path -LiteralPath $cert) -or -not (Test-Path -LiteralPath $key)) {
        throw 'El certificado HTTPS está incompleto. Conserva o restaura cert.pem y key.pem según el README.'
    }

    if ($RenewCertificate) {
        & (Join-Path $PSScriptRoot 'Renew-VayxerCertificate.ps1') -TlsDirectory $tls
    }

    Write-Host 'Preparando Vayxer. El primer arranque puede tardar unos minutos...'
    $profile = @('-f', 'compose.yaml', '-f', 'tls.compose.yaml')
    docker compose @profile config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Revisa la configuración local con docker compose config --quiet.' }
    docker compose @profile up -d --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) {
        docker compose @profile ps -a
        throw 'Revisa Docker Desktop y los registros con docker compose logs --tail 40. Si el puerto está ocupado, cambia PORT en .env.'
    }

    $ports = @(docker compose @profile port gateway 443 2>$null)
    $portExit = $LASTEXITCODE
    $binding = ([string]($ports | Select-Object -First 1)).Trim()
    if ($portExit -ne 0 -or $binding -notmatch '^127\.0\.0\.1:(\d+)$') {
        throw 'No se encontró el puerto HTTPS local. Comprueba el servicio gateway y la variable TLS_PORT de .env.'
    }
    $url = "https://127.0.0.1:$($Matches[1])"
    $deadline = [DateTime]::UtcNow.AddSeconds(35)
    $ready = $false
    do {
        try {
            $body = curl.exe --cacert local-tls/cert.pem --fail --silent --max-time 3 "$url/api/ready"
            if ($LASTEXITCODE -eq 0 -and ($body | ConvertFrom-Json).status -eq 'ready') {
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
    docker compose @profile exec -T monitor python auth_store.py --needs-setup
    $setupStatus = $LASTEXITCODE
    if ($setupStatus -eq 3) {
        Write-Host 'Define las contraseñas de las cuentas iniciales. La terminal no mostrará lo que escribas.'
        docker compose @profile exec monitor python auth_store.py --initial
        if ($LASTEXITCODE -ne 0) { throw 'No se completó la configuración de las cuentas. Vuelve a abrir Vayxer desde una terminal interactiva.' }
    } elseif ($setupStatus -ne 0) {
        throw 'No se pudo comprobar el estado de las cuentas iniciales.'
    }

    Write-Host "Vayxer listo en $url"
    if (-not $NoBrowser) {
        $edge = @(
            (Join-Path ${env:ProgramFiles(x86)} 'Microsoft/Edge/Application/msedge.exe'),
            (Join-Path $env:ProgramFiles 'Microsoft/Edge/Application/msedge.exe'),
            (Join-Path $env:LOCALAPPDATA 'Microsoft/Edge/Application/msedge.exe')
        ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
        if (-not $edge) {
            throw 'Microsoft Edge no está instalado en una ruta conocida. Instálalo y vuelve a abrir Vayxer.'
        }

        & (Join-Path $PSScriptRoot 'Trust-VayxerCertificate.ps1') -CertificatePath $cert -Port ([int]([Uri]$url).Port)
        $hasher = [Security.Cryptography.SHA256]::Create()
        try {
            $thumb = [BitConverter]::ToString($hasher.ComputeHash([IO.File]::ReadAllBytes($cert))).Replace('-','')
        } finally { $hasher.Dispose() }
        $edgeProfile = Join-Path $env:LOCALAPPDATA "Vayxer/Edge/trusted-$thumb"
        Start-Process -FilePath $edge -ArgumentList @(
            ('--user-data-dir="' + $edgeProfile + '"'),
            '--no-first-run',
            '--new-window',
            $url
        )
    }
    exit 0
} catch {
    Write-Host "Vayxer: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
