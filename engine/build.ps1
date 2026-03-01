$ErrorActionPreference = 'Stop'

if (-not (Test-Path 'engine/build')) {
    New-Item -ItemType Directory -Path 'engine/build' | Out-Null
}

cmake -S engine -B engine/build
cmake --build engine/build --config Debug

$testCandidates = @(
    'engine/build/Debug/tes_engine_tests.exe',
    'engine/build/tes_engine_tests.exe',
    'engine/build/tes_engine_tests'
)

$testBinary = $testCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $testBinary) {
    throw 'Could not locate tes_engine_tests binary in expected build output paths.'
}

& $testBinary
