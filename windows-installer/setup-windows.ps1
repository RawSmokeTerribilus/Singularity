# setup-windows.ps1  —  Singularity Suite v3.0.1 Windows installer
# ----------------------------------------------------------------------------
# Omnipotent 3-file install (parity with final-user-install.sh):
#   docker-compose.yml + install-windows.bat + setup-windows.ps1  +  the image.
# No repo clone required. Config templates AND tracker modules are extracted
# live from the image (rawsmoke/singularity-suite:latest), so this script never
# carries stale embedded config and stays in sync with whatever version you pull.
# ----------------------------------------------------------------------------

$ErrorActionPreference = "Stop"
$Image = "rawsmoke/singularity-suite:latest"

$BaseDir   = Get-Location
$ConfigDir = Join-Path $BaseDir "config"
$WorkDir   = Join-Path $BaseDir "work_data"

Write-Host "--- Configurando Arsenal Singularity en: $BaseDir ---" -ForegroundColor Cyan

# --- 0. PRECHECK: Docker disponible ------------------------------------------
try { docker version --format '{{.Server.Version}}' | Out-Null }
catch {
    Write-Host "ERROR: Docker no responde. Arranca Docker Desktop y reintenta." -ForegroundColor Red
    exit 1
}

# --- 1. ESTRUCTURA DE DIRECTORIOS (paridad con final-user-install.sh) --------
$Dirs = @(
    $ConfigDir,
    "$WorkDir\mass_editor",
    "$WorkDir\logs\MKVerything",
    "$WorkDir\logs\RawLoadrr",
    "$WorkDir\logs\mkverything",
    "$WorkDir\logs\rawloadrr",
    "$WorkDir\logs\csi_log",
    "$WorkDir\reports",
    "$WorkDir\tmp\qbit_backup",
    "$WorkDir\tmp\TEMP_RESCUE",
    "$WorkDir\trackers",
    "$WorkDir\cookies",
    "$WorkDir\qbit_backup",
    "$WorkDir\tor\data",
    "$WorkDir\tor\logs",
    "$BaseDir\media"
)
foreach ($Dir in $Dirs) {
    if (-not (Test-Path -LiteralPath $Dir)) {
        New-Item -ItemType Directory -Path $Dir -Force | Out-Null
        Write-Host "Created: $Dir" -ForegroundColor Green
    }
}

# --- 2. PLACEHOLDERS (evita que Docker cree carpetas en vez de archivos) -----
$TouchFiles = @(
    "$ConfigDir\cookies.txt",
    "$WorkDir\mass_editor\ids.txt",
    "$WorkDir\mass_editor\completados.txt",
    "$WorkDir\mass_editor\completados_img.txt",
    "$WorkDir\mass_editor\mapeo_maestro.json",
    "$WorkDir\mass_editor\titulos_mapa.json",
    "$WorkDir\mass_editor\mapeo_por_titulo.json"
)
foreach ($File in $TouchFiles) {
    if (-not (Test-Path -LiteralPath $File)) {
        New-Item -ItemType File -Path $File -Force | Out-Null
        Write-Host "Touched: $File" -ForegroundColor Yellow
    }
}

# JSON vacios -> inicializa a "{}" si tienen 0 bytes
$JsonFiles = @(
    "$WorkDir\mass_editor\mapeo_maestro.json",
    "$WorkDir\mass_editor\titulos_mapa.json",
    "$WorkDir\mass_editor\mapeo_por_titulo.json"
)
foreach ($Json in $JsonFiles) {
    if ((Get-Item -LiteralPath $Json).Length -eq 0) {
        "{}" | Out-File -FilePath $Json -Encoding utf8 -NoNewline
    }
}

# --- 3. EXTRAER CONFIG + TRACKERS DESDE LA IMAGEN ----------------------------
# La imagen es la fuente de verdad: trae /app/config/*.example y los 53 modulos
# de tracker horneados. Un contenedor desechable los saca; nada se embebe aqui.
$needConfig = -not (Test-Path -LiteralPath "$ConfigDir\config.py")
$needTrackers = (Get-ChildItem -LiteralPath "$WorkDir\trackers" -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0

if ($needConfig -or $needTrackers) {
    # Imagen local? si no, baja (mismo guard que el Bug 2 de Linux: no clobber del build local)
    docker image inspect $Image 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Bajando imagen $Image ..." -ForegroundColor Cyan
        docker pull $Image | Out-Null
    }

    $ExtractDir = Join-Path $env:TEMP ("sing_extract_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $ExtractDir -Force | Out-Null
    $Cid = (docker create $Image).Trim()
    try {
        # 3a. Plantillas de config (visibles + para copy_if_missing)
        docker cp "${Cid}:/app/config/." $ExtractDir | Out-Null
        Get-ChildItem -LiteralPath $ExtractDir -Filter "*.example" | ForEach-Object {
            $dst = Join-Path $ConfigDir $_.Name
            if (-not (Test-Path -LiteralPath $dst)) { Copy-Item $_.FullName $dst }
        }

        # 3b. SIEMBRA DE TRACKERS (fix Bug 1: dir vacio enmascara los modulos del image)
        if ($needTrackers) {
            Write-Host "Infundiendo trackers desde la imagen..." -ForegroundColor Cyan
            docker cp "${Cid}:/app/RawLoadrr/src/trackers/." "$WorkDir\trackers" | Out-Null
        }
    }
    finally {
        docker rm $Cid | Out-Null
        Remove-Item -LiteralPath $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# --- 4. CONFIG REAL desde plantillas (copy_if_missing) -----------------------
function Copy-IfMissing($src, $dst) {
    if ((Test-Path -LiteralPath $src) -and (-not (Test-Path -LiteralPath $dst))) {
        Copy-Item $src $dst
        Write-Host "Creado: $(Split-Path $dst -Leaf) desde plantilla" -ForegroundColor Cyan
    }
}
Copy-IfMissing "$ConfigDir\.env.example"                  "$ConfigDir\.env"
Copy-IfMissing "$ConfigDir\singularity_config.py.example" "$ConfigDir\singularity_config.py"
Copy-IfMissing "$ConfigDir\config.py.example"             "$ConfigDir\config.py"
Copy-IfMissing "$ConfigDir\mass_config.py.example"        "$ConfigDir\mass_config.py"

# --- 5. VALIDACION de config obligatoria -------------------------------------
$Required = @(
    "$ConfigDir\.env",
    "$ConfigDir\singularity_config.py",
    "$ConfigDir\config.py",
    "$ConfigDir\mass_config.py"
)
foreach ($r in $Required) {
    if (-not (Test-Path -LiteralPath $r)) {
        Write-Host "ERROR: falta archivo requerido: $r" -ForegroundColor Red
        Write-Host "       La imagen no trajo la plantilla. Verifica 'docker pull $Image'." -ForegroundColor Red
        exit 1
    }
}

# --- 6. WRAPPERS .bat --------------------------------------------------------
# singularity.bat (lanza el menu/orquestador)
"@echo off`r`ndocker exec -it singularity_core python3 singularity.py" |
    Out-File -FilePath "$BaseDir\singularity.bat" -Encoding ascii
Write-Host "Generado: singularity.bat (lanza el menu)" -ForegroundColor Magenta

# singularity-shell.bat (terminal del contenedor)
"@echo off`r`ndocker exec -it singularity_core /bin/bash" |
    Out-File -FilePath "$BaseDir\singularity-shell.bat" -Encoding ascii
Write-Host "Generado: singularity-shell.bat" -ForegroundColor Magenta

# up.bat / down.bat
"@echo off`r`ndocker compose up -d`r`necho Singularity Core iniciado." |
    Out-File -FilePath "$BaseDir\up.bat" -Encoding ascii
"@echo off`r`ndocker compose down" |
    Out-File -FilePath "$BaseDir\down.bat" -Encoding ascii
Write-Host "Generado: up.bat / down.bat" -ForegroundColor Magenta

# --- 7. FIN ------------------------------------------------------------------
Write-Host "`nINSTALACION COMPLETADA." -ForegroundColor Green
Write-Host "--------------------------------------------------------"
Write-Host "1. Edita tus credenciales en la carpeta 'config' (.env, config.py, singularity_config.py, mass_config.py)"
Write-Host "2. Ejecuta 'up.bat' para levantar el contenedor"
Write-Host "3. Ejecuta 'singularity.bat' para usar la suite"
Write-Host "--------------------------------------------------------"
