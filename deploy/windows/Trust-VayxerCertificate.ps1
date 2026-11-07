[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$CertificatePath,
    [Parameter(Mandatory)][int]$Port,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

function Test-VayxerTrust {
    param([Security.Cryptography.X509Certificates.X509Certificate2]$Certificate)
    $store = [Security.Cryptography.X509Certificates.X509Store]::new('Root', 'CurrentUser')
    try {
        $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
        $found = $store.Certificates.Find([Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint, $Certificate.Thumbprint, $false)
        foreach ($entry in $found) {
            if ([Convert]::ToBase64String($entry.RawData) -ceq [Convert]::ToBase64String($Certificate.RawData)) { return $true }
        }
        return $false
    } finally { $store.Close() }
}

$pem = Get-Content -LiteralPath $CertificatePath -Raw
$verifyCode = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../../backend/tls_verify.py') -Raw -Encoding UTF8
$encodedCode = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($verifyCode))
$pem | docker compose -f compose.yaml -f tls.compose.yaml exec -T monitor python -c "import base64;exec(base64.b64decode('$encodedCode'))" | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'El certificado local no superó la verificación. No se modificó la confianza.' }
$certificate = [Security.Cryptography.X509Certificates.X509Certificate2]::new($CertificatePath)
$expected = [Convert]::ToBase64String($certificate.RawData)
$validatePeer = {
    param($sender, $remoteCertificate, $chain, $errors)
    return $null -ne $remoteCertificate -and [Convert]::ToBase64String($remoteCertificate.GetRawCertData()) -ceq $expected
}.GetNewClosure()
$tcp = [Net.Sockets.TcpClient]::new()
try {
    $connection = $tcp.ConnectAsync('127.0.0.1', $Port)
    if (-not $connection.Wait(5000)) { throw 'El puerto HTTPS local no respondió.' }
    $stream = [Net.Security.SslStream]::new($tcp.GetStream(), $false, [Net.Security.RemoteCertificateValidationCallback]$validatePeer)
    try {
        $stream.ReadTimeout = 5000
        $stream.WriteTimeout = 5000
        $stream.AuthenticateAsClient('127.0.0.1')
    } finally { $stream.Dispose() }
} finally { $tcp.Dispose() }
Write-Host 'El servidor presenta exactamente el certificado local verificado.'
if ($ValidateOnly) { return }

if (-not (Test-VayxerTrust -Certificate $certificate)) {
    Write-Host 'Vayxer necesita confiar en este certificado HTTPS local para abrir Edge sin advertencias.'
    Write-Host "Huella SHA-1 del certificado: $($certificate.Thumbprint)"
    Write-Host 'Se agregará solo este certificado al almacén de confianza de tu usuario de Windows.'
    $answer = Read-Host '¿Aceptas? Escribe SI para importar; cualquier otra respuesta cancela'
    if ($answer -cne 'SI') { throw 'No se importó el certificado. Vuelve a ejecutar Vayxer cuando quieras autorizarlo.' }
    $store = [Security.Cryptography.X509Certificates.X509Store]::new('Root', 'CurrentUser')
    try {
        $store.Open([Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
        $store.Add($certificate)
    } finally { $store.Close() }
}
if (-not (Test-VayxerTrust -Certificate $certificate)) { throw 'Windows no confirmó la confianza del certificado local.' }

$ready = curl.exe --fail --silent --max-time 5 "https://127.0.0.1:$Port/api/ready"
if ($LASTEXITCODE -ne 0 -or ($ready | ConvertFrom-Json).status -ne 'ready') {
    throw 'HTTPS no confirmó confianza y disponibilidad. No se abrirá Edge.'
}
