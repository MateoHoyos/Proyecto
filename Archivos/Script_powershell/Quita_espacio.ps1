<#
  Quita_espacio.ps1
  - Reemplaza espacios por guiones bajos en nombres de carpetas.
  - Reemplaza " - " por "_-_".
  - Soporta ejecución recursiva.
  - Incluye modo "dry-run" para probar sin renombrar.
#>

param(
    [string]$Path = "C:\Users\mhoyosme\Downloads\RECT2",
    [switch]$Recurse,
    [switch]$DryRun
)

# Obtener carpetas (si es recursivo, ordenar por profundidad para renombrar hijos antes que padres)
$folders = Get-ChildItem -Path $Path -Directory -Force -ErrorAction SilentlyContinue
if ($Recurse) {
    $folders = Get-ChildItem -Path $Path -Directory -Recurse -Force -ErrorAction SilentlyContinue
}

# Ordenar por longitud del path de mayor a menor (para procesar subcarpetas primero)
$folders = $folders | Sort-Object { $_.FullName.Length } -Descending

foreach ($f in $folders) {
    $oldName = $f.Name

    # Reemplazo: " - " -> "_-_" ; cualquier whitespace -> "_"
    $newName = $oldName -replace ' - ', '_-_' -replace '\s+', '_'

    if ($oldName -ne $newName) {
        $oldFull = $f.FullName
        $newFull = Join-Path -Path $f.Parent.FullName -ChildPath $newName

        # Si ya existe, añadir contador (_1, _2, ...)
        $candidate = $newFull
        $i = 1
        while (Test-Path -LiteralPath $candidate) {
            $candidate = Join-Path -Path $f.Parent.FullName -ChildPath ("{0}_{1}" -f $newName, $i)
            $i++
        }

        if ($DryRun) {
            Write-Host "[DRY-RUN] $oldFull  ->  $candidate"
        }
        else {
            try {
                Rename-Item -LiteralPath $oldFull -NewName (Split-Path -Leaf $candidate)
                Write-Host "Renombrado: $oldFull  ->  $candidate"
            }
            catch {
                Write-Warning "Error al renombrar '$oldFull': $_"
            }
        }
    }
}
