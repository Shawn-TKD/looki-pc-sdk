[CmdletBinding()]
param(
    [string]$Address,
    [switch]$Pair,
    [switch]$Renew,
    [switch]$Status
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Looki = Join-Path $RepoRoot '.venv\Scripts\looki.exe'

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($Launcher) {
        & $Launcher.Source -3 -m venv (Join-Path $RepoRoot '.venv')
    } else {
        $Python = Get-Command python -ErrorAction Stop
        & $Python.Source -m venv (Join-Path $RepoRoot '.venv')
    }
}

& $VenvPython -m pip install --upgrade pip setuptools
& $VenvPython -m pip install -e $RepoRoot
& $Looki doctor

if (($Pair -or $Status) -and -not $Address) {
    throw '-Address is required with -Pair or -Status'
}

if ($Pair) {
    $Arguments = @('pair', '--address', $Address)
    if ($Renew) {
        $Arguments += '--renew'
    }
    & $Looki @Arguments
}

if ($Status) {
    & $Looki status --address $Address --trace
}
