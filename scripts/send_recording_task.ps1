param(
    [Parameter(Mandatory = $true)]
    [string]$Batch,
    [string]$GroupId
)

$ErrorActionPreference = "Stop"
$cccc = Join-Path $env:APPDATA "Python\Python312\Scripts\cccc.exe"
if (-not (Test-Path -LiteralPath $cccc)) { throw "CCCC is not installed: $cccc" }
$batchPath = (Resolve-Path -LiteralPath $Batch).Path
$message = @(
    "Execute the two-screenshot Screenshot-to-App recording batch.",
    "",
    "Batch manifest: $batchPath",
    "",
    "Process FastBite then MallLite. Before and after every phase, print concise Simplified-Chinese terminal lines for visual understanding, frontend scaffolding, browser acceptance, and delivery. Use .\\scripts\\python.cmd scripts/worker_progress.py for the evidence log (do not call the unavailable python alias).",
    "Read worker/ROLE.md and the installed frontend-design skill. Use fictional brands and local CSS/SVG assets only. Do not copy source logos, brands, product images, prices, or wording.",
    "Browser-test each result, create worker-delivery.json, and create one local Git commit after both runs PASS. Do not create or push a GitHub repository until explicit repository and approval are provided."
) -join [Environment]::NewLine
$arguments = @("tracked-send", $message, "--to", "mvp-worker", "--title", "Two screenshot recording batch", "--outcome", "Both apps have PASS delivery receipts, previews, Chinese phase logs, and one local Git commit.")
if ($GroupId) { $arguments += @("--group", $GroupId) }
& $cccc @arguments
