param(
    [Parameter(Position = 0)]
    [ValidateSet("add", "brief")]
    [string]$Command
)

if (-not $Command) {
    Write-Host "Usage: .\fitness.ps1 add"
    Write-Host "       .\fitness.ps1 brief"
    exit 1
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source -m cli.main $Command
    exit $LASTEXITCODE
}

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    & $pyLauncher.Source -3 -m cli.main $Command
    exit $LASTEXITCODE
}

$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path $bundledPython) {
    & $bundledPython -m cli.main $Command
    exit $LASTEXITCODE
}

Write-Error "Python was not found. Install Python or run this inside Codex with the bundled runtime available."
exit 1
