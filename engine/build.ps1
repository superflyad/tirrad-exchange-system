$ErrorActionPreference = 'Stop'

$cmakeCommand = Get-Command cmake -ErrorAction SilentlyContinue
if (-not $cmakeCommand) {
    Write-Host 'CMake was not found on PATH.' -ForegroundColor Red
    Write-Host 'Install it with: winget install --id Kitware.CMake -e' -ForegroundColor Yellow
    exit 1
}

$buildDir = 'engine/build'
if (-not (Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

cmake -S engine -B $buildDir
cmake --build $buildDir --config Debug

$generatorName = (Get-Content "$buildDir/CMakeCache.txt" |
    Where-Object { $_ -like 'CMAKE_GENERATOR:*' } |
    ForEach-Object { $_.Split('=')[1] } |
    Select-Object -First 1)

$testCandidates = @(
    "$buildDir/Debug/tes_engine_tests.exe",
    "$buildDir/tes_engine_tests.exe",
    "$buildDir/tes_engine_tests"
)
$testBinary = $testCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

Write-Host "Detected CMake generator: $generatorName"
Write-Host "Build directory: $buildDir"
Write-Host "Resolved test executable path: $testBinary"

$ctestCommand = Get-Command ctest -ErrorAction SilentlyContinue
if ($ctestCommand) {
    ctest --test-dir $buildDir -C Debug --output-on-failure
    if ($LASTEXITCODE -eq 0) {
        exit 0
    }

    Write-Host 'ctest failed; falling back to direct test executable invocation.' -ForegroundColor Yellow
}

if (-not $testBinary) {
    throw 'Could not locate tes_engine_tests binary in expected build output paths.'
}

& $testBinary
