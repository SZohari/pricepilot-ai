$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$candidates = @(
    (Join-Path $PSScriptRoot ".venv-web\Scripts\python.exe"),
    (Join-Path $PSScriptRoot ".venv-review\Scripts\python.exe"),
    (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")
)
$systemPython = Get-Command python -ErrorAction SilentlyContinue
if ($systemPython) { $candidates += $systemPython.Source }
$candidates += Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
foreach ($candidate in $candidates) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    $ErrorActionPreference = "Continue"
    & $candidate -c "import sys; sys.path.insert(0,'.'); from run import prepare_dependencies; prepare_dependencies()" 2>$null
    $probeExit = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($probeExit -eq 0) {
        & $candidate run.py @args
        exit $LASTEXITCODE
    }
}
Write-Host ""
Write-Host "Python or web dependencies are not ready." -ForegroundColor Yellow
Write-Host "Install Python 3.12 from https://www.python.org/downloads/"
Write-Host "Then run these commands in this folder:"
Write-Host "  python -m pip install -r requirements-web.txt"
Write-Host "  python run.py"
exit 1
