$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 "$PSScriptRoot\scripts\start_local.py" @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python "$PSScriptRoot\scripts\start_local.py" @args
} else {
    Write-Error "Python 3.10+ was not found. Install Python, then retry."
}
