$path = "C:\Users\mhoyosme\Downloads\RECT2\11_-_CORRIENTE_DC_DE_LA_CARGA"



# Meses fijos en orden
$meses = @(
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
)

# Obtiene archivos y les añade una SortKey que hace "natural sort"
$files = Get-ChildItem -Path $path -File | ForEach-Object {
    $name = $_.Name
    # Reemplaza cada grupo de dígitos por un número con padding a 10 dígitos (permite ordenar numéricamente)
    $sortKey = [regex]::Replace($name, '(\d+)', { param($m) ('{0:D10}' -f [int]$m.Value) })
    # Devuelve objeto con la clave para ordenar
    [PSCustomObject]@{
        File = $_
        SortKey = $sortKey
    }
} | Sort-Object -Property SortKey

$index = 1
foreach ($entry in $files) {
    $file = $entry.File
    $ext = $file.Extension

    # Saltar si ya tiene formato XX_Mmm_YYYY al inicio
    if ($file.BaseName -match '^\d{2}_[A-Za-z]{3}_\d{4}') {
        Write-Host "Saltando (ya renombrado): $($file.Name)"
        $index++
        continue
    }

    if ($index -le 12) {
        $num = "{0:00}" -f $index
        $month = $meses[$index - 1]
        $year = 2025
        $newName = "${num}_${month}_${year}${ext}"
    } else {
        $num = "{0:00}" -f $index
        $newName = "${num}_Extra_2025${ext}"
    }

    # Evitar colisiones: si ya existe, agrega (1), (2), ...
    $finalName = $newName
    $counter = 1
    while (Test-Path (Join-Path $path $finalName)) {
        $baseNoExt = $newName.Substring(0, $newName.Length - $ext.Length)
        $finalName = "{0}({1}){2}" -f $baseNoExt, $counter, $ext
        $counter++
    }

    Rename-Item -LiteralPath $file.FullName -NewName $finalName
    Write-Host "Renombrado: $($file.Name) → $finalName"

    $index++
}

