[CmdletBinding()]
param([Parameter(Mandatory)][string]$TlsDirectory)

$ErrorActionPreference = 'Stop'
$stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')
$staging = Join-Path $TlsDirectory "renewal-$stamp"
$backup = Join-Path $TlsDirectory "previous-$stamp"
New-Item -ItemType Directory -Path $staging -ErrorAction Stop | Out-Null
Write-Host 'Generando un nuevo certificado local de 30 días...'
docker compose run --rm --no-deps -T --user 0 --volume "${staging}:/tls" monitor python tls_setup.py
if ($LASTEXITCODE -ne 0) { throw 'No se generó el nuevo certificado. Se conserva el par anterior.' }
foreach ($name in @('cert.pem', 'key.pem')) {
    if (-not (Test-Path -LiteralPath (Join-Path $staging $name))) { throw 'La renovación quedó incompleta. Se conserva el par anterior.' }
}
New-Item -ItemType Directory -Path $backup -ErrorAction Stop | Out-Null
foreach ($name in @('cert.pem', 'key.pem', 'vayxer-local.sha256')) {
    $existing = Join-Path $TlsDirectory $name
    if (Test-Path -LiteralPath $existing) { Copy-Item -LiteralPath $existing -Destination $backup -ErrorAction Stop }
}
docker compose -f compose.yaml -f tls.compose.yaml stop gateway
if ($LASTEXITCODE -ne 0) { throw 'No se pudo detener el gateway. Se conserva el par anterior.' }
try {
    foreach ($name in @('cert.pem', 'key.pem', 'vayxer-local.sha256')) {
        Copy-Item -LiteralPath (Join-Path $staging $name) -Destination (Join-Path $TlsDirectory $name) -Force -ErrorAction Stop
    }
} catch {
    foreach ($name in @('cert.pem', 'key.pem')) {
        Copy-Item -LiteralPath (Join-Path $backup $name) -Destination (Join-Path $TlsDirectory $name) -Force
    }
    docker compose -f compose.yaml -f tls.compose.yaml start gateway | Out-Host
    throw
}
Write-Host "Certificado renovado. Respaldo local del par anterior: $backup"
