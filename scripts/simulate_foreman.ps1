param(
    [Parameter(Mandatory = $true)]
    [string]$Screenshot,
    [Parameter(Mandatory = $true)]
    [string]$RunId,
    [string]$AppName = "FastBite"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$source = (Resolve-Path -LiteralPath $Screenshot).Path
$sample = Join-Path $root "contracts\mvp-contract.sample.json"
$target = Join-Path $root "contracts\mvp-contract.json"
$python = Join-Path $root "scripts\python.cmd"
if (-not (Test-Path -LiteralPath $python)) { throw "Worker Python launcher is missing: $python" }

$contract = Get-Content -Raw -LiteralPath $sample | ConvertFrom-Json
$contract.run_id = $RunId
$contract.source_screenshot.path = $source
$contract.app.name = $AppName
$contract | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $target -Encoding utf8

& $python (Join-Path $root "scripts\prepare_run.py") --contract $target
