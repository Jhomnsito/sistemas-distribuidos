$ErrorActionPreference = 'Stop'

try {
    $root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
    $launcher = Join-Path $root 'Vayxer.cmd'
    $icon = Join-Path $PSScriptRoot 'Vayxer-flecha.ico'
    if (-not (Test-Path -LiteralPath $launcher) -or -not (Test-Path -LiteralPath $icon)) {
        throw 'Descomprime todo el proyecto y ejecuta el instalador desde la carpeta descomprimida.'
    }
    $desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
    if (-not (Test-Path -LiteralPath $desktop -PathType Container)) { throw 'No se encontró la carpeta Escritorio.' }
    $link = Join-Path $desktop 'Vayxer.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($link)
    if ((Test-Path -LiteralPath $link) -and $shortcut.TargetPath -ne $launcher) {
        throw 'Ya existe un acceso directo Vayxer de otra carpeta. Muévelo o renómbralo para conservarlo.'
    }
    $shortcut.TargetPath = $launcher
    $shortcut.WorkingDirectory = $root
    $shortcut.IconLocation = "$icon,0"
    $shortcut.Description = 'Inicia Vayxer y abre el panel de pedidos'
    $shortcut.Save()
    Write-Host "Acceso directo listo: $link"
} catch {
    Write-Host "Vayxer: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
