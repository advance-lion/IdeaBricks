param(
    [Parameter(Mandatory = $true)]
    [string]$Screenshot,
    [string]$RunId,
    [string]$AppName = "SparkMVP",
    [switch]$Dispatch,
    [string]$GroupId = "g_c3e3880e9f6c"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$source = (Resolve-Path -LiteralPath $Screenshot).Path
if (-not $RunId) { $RunId = "trial-" + (Get-Date -Format "yyyyMMdd-HHmmss") }

& (Join-Path $PSScriptRoot "simulate_foreman.ps1") -Screenshot $source -RunId $RunId -AppName $AppName
if ($LASTEXITCODE -ne 0) { throw "Could not prepare the Worker run." }

$contract = (Resolve-Path -LiteralPath (Join-Path $root "contracts\mvp-contract.json")).Path
$runDir = Join-Path $root ("runs\" + $RunId)
Write-Host "[Worker Intake] Prepared run: $RunId"
Write-Host "[Worker Intake] Contract: $contract"
Write-Host "[Worker Intake] Output folder: $runDir"

if (-not $Dispatch) {
    Write-Host "[Worker Intake] Prepared only. Add -Dispatch to send this contract to CCCC."
    exit 0
}

cccc actor start mvp-worker --group $GroupId | Out-Host
$task = @"
Execute the Screenshot-to-App MVP Worker now.

Contract (absolute path): $contract
Run ID: $RunId
Progress batch ID: live-trials

Use the screenshot only as a layout and interaction reference. Generate a fictional brand with local assets. For every phase, write a progress event using .\scripts\python.cmd scripts\worker_progress.py --batch live-trials --run $RunId. Use these exact message keys: visual STARTED/PASS = generic-visual-start/generic-visual-pass; scaffold = generic-scaffold-start/generic-scaffold-pass; browser = generic-browser-start/generic-browser-pass; delivery = generic-delivery-start/generic-delivery-pass. Run browser acceptance and finalize delivery. Reply only with PASS/FAIL and the absolute delivery artifact paths.
"@
cccc tracked-send $task --group $GroupId --to mvp-worker --title "Screenshot-to-App trial: $RunId" --outcome "worker-delivery.json is PASS and preview.png plus acceptance-report.json exist" --idempotency-key "intake-$RunId" | Out-Host
Write-Host "[Worker Intake] Dispatched to CCCC actor mvp-worker. Open http://127.0.0.1:8848/ui/ to watch the terminal."
