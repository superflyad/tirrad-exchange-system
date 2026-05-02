param(
    [string]$Preset = "debug-msvc-python",
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

if (-not $PythonExe) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        $PythonExe = $cmd.Source
    }
}

if (-not $PythonExe) {
    throw "Python executable not found in PATH. Pass -PythonExe <path>."
}

$Pybind11Dir = & $PythonExe -m pybind11 --cmakedir
if (-not $Pybind11Dir) {
    throw "Unable to resolve pybind11 cmake dir using '$PythonExe -m pybind11 --cmakedir'."
}

Write-Host "Using Python executable: $PythonExe"
Write-Host "Using pybind11_DIR: $Pybind11Dir"

cmake --preset $Preset `
    -DPython3_EXECUTABLE="$PythonExe" `
    -Dpybind11_DIR="$Pybind11Dir"
