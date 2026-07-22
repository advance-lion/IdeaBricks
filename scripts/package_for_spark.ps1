param(
    [string]$Output = "exports\forge-dgx-spark-test.zip"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$destination = Join-Path $root $Output
$stage = Join-Path ([System.IO.Path]::GetTempPath()) ("forge-dgx-" + [guid]::NewGuid().ToString("N"))
$packageRoot = Join-Path $stage "forge-dgx-spark-test"

New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
try {
    $files = & git -C $root ls-files --cached --others --exclude-standard
    if ($LASTEXITCODE -ne 0) { throw "Unable to enumerate repository files with git." }
    foreach ($relative in $files) {
        $normalized = $relative.Replace('\', '/')
        if ($normalized -eq $Output.Replace('\', '/') -or $normalized -like 'exports/*.zip') { continue }
        # The persistent snapshot and summary are enough for a demo run. The
        # raw catalog mirrors are only needed by the optional maintenance job.
        if ($normalized -like 'agents/idea-agent/catalog/data/*' -or $normalized -like 'agents/cli-researcher/cli-catalog/catalog/data/*') { continue }
        # Previous deliveries and local tool caches do not belong in a clean
        # Spark test upload. New evidence is generated on the target host.
        if ($normalized -like 'runs/*' -or $normalized -like 'handoffs/*' -or $normalized -like 'logs/*' -or $normalized -like 'exports/*' -or $normalized -like 'inputs/*' -or $normalized -like 'contracts/live-trials/*' -or $normalized -like '.tools/*') { continue }
        $source = Join-Path $root $relative
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { continue }
        $target = Join-Path $packageRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $source -Destination $target
    }
    # These runtime assets are intentionally gitignored because they are
    # generated/large locally, but the deployed demo needs them: Foreman
    # exposes catalog/data as provenance and the stage ships two authorized
    # reference screenshots for the KFC/Taobao demo controls.
    $requiredFolders = @(
        "agents\cli-researcher\cli-catalog\catalog\data",
        "inputs\screenshot-to-app-recording-001"
    )
    foreach ($relativeFolder in $requiredFolders) {
        $sourceFolder = Join-Path $root $relativeFolder
        if (-not (Test-Path -LiteralPath $sourceFolder -PathType Container)) { continue }
        Get-ChildItem -LiteralPath $sourceFolder -Recurse -File | ForEach-Object {
            $relativeFile = $_.FullName.Substring($root.Length).TrimStart('\', '/')
            $target = Join-Path $packageRoot $relativeFile
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $target -Force
        }
    }
    # Ship the installed design skill with the deployment so Codex CLI on the
    # target host can follow the same worker instruction without depending on
    # the packager's user profile.
    $frontendDesignSkill = Join-Path $HOME ".codex\skills\anthropics-frontend-design"
    $frontendDesignEntry = Join-Path $frontendDesignSkill "SKILL.md"
    if (-not (Test-Path -LiteralPath $frontendDesignEntry -PathType Leaf)) {
        throw "Missing required frontend design skill: $frontendDesignEntry"
    }
    Get-ChildItem -LiteralPath $frontendDesignSkill -Recurse -File | ForEach-Object {
        $relativeFile = $_.FullName.Substring($frontendDesignSkill.Length).TrimStart('\', '/')
        $target = Join-Path $packageRoot (Join-Path "skills\anthropics-frontend-design" $relativeFile)
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $target -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
    Compress-Archive -LiteralPath $packageRoot -DestinationPath $destination -CompressionLevel Optimal -Force
    Write-Output "Created $destination"
}
finally {
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
}
