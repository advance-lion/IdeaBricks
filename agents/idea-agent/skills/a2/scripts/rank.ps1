[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RequestPath,
    [Parameter(Mandatory = $true)][string]$GenerationPath,
    [Parameter(Mandatory = $true)][string]$EvaluationInputPath,
    [Parameter(Mandatory = $true)][string]$EvaluationPath,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:RunIdPattern = '^a2_[0-9]{8}_[0-9]{6}_[0-9a-f]{6}$'

$dimensions = @('user_value', 'feasibility', 'generality', 'innovation', 'visual_expression')

function Read-JsonFile {
    param([string]$Path, [string]$Label)
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label not found: $Path"
    }
    try {
        $raw = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $Path).Path, [System.Text.Encoding]::UTF8)
        if ([string]::IsNullOrWhiteSpace($raw)) { throw 'file is empty' }
        $parsed = $raw | ConvertFrom-Json
        return ,$parsed
    }
    catch {
        throw "Invalid $Label JSON at ${Path}: $($_.Exception.Message)"
    }
}

function Has-Property {
    param($Object, [string]$Name)
    return ($null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name])
}

function Require-Property {
    param($Object, [string]$Name, [string]$Context)
    if (-not (Has-Property -Object $Object -Name $Name)) {
        throw "$Context is missing property '$Name'"
    }
    return ,$Object.PSObject.Properties[$Name].Value
}

function Require-String {
    param($Object, [string]$Name, [string]$Context)
    $value = Require-Property -Object $Object -Name $Name -Context $Context
    if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value)) {
        throw "$Context property '$Name' must be a non-empty string"
    }
    return $value.Trim()
}

function Require-Identifier {
    param($Object, [string]$Name, [string]$Context)
    $value = Require-Property -Object $Object -Name $Name -Context $Context
    if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value) -or $value -cne $value.Trim()) {
        throw "$Context property '$Name' must be a non-empty string without surrounding whitespace"
    }
    return $value
}

function Require-RunId {
    param($Object, [string]$Context)
    $value = Require-Identifier -Object $Object -Name 'run_id' -Context $Context
    if ($value -cnotmatch $script:RunIdPattern) {
        throw "$Context property 'run_id' must match a2_yyyyMMdd_HHmmss_<six-lowercase-hex>"
    }
    return $value
}

function Require-Sha256 {
    param($Object, [string]$Name, [string]$Context)
    $value = Require-String -Object $Object -Name $Name -Context $Context
    if ($value -cnotmatch '^[0-9a-f]{64}$') {
        throw "$Context property '$Name' must be a lowercase SHA-256 value"
    }
    return $value
}

function Get-FileSha256 {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "generation not found: $Path"
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Path).Path)
        return [System.BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Get-ValueSha256 {
    param($Value)
    $json = ConvertTo-Json -InputObject $Value -Depth 50 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return [System.BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Get-EvaluationInputPayload {
    param($EvaluationInput)
    return [pscustomobject][ordered]@{
        run_id = $EvaluationInput.run_id
        generation_sha256 = $EvaluationInput.generation_sha256
        product_context = $EvaluationInput.product_context
        capability_chains = @($EvaluationInput.capability_chains)
        ideas = @($EvaluationInput.ideas)
        tools = @($EvaluationInput.tools)
        rubric = $EvaluationInput.rubric
    }
}

function Require-Array {
    param($Object, [string]$Name, [string]$Context, [switch]$AllowEmpty)
    $value = Require-Property -Object $Object -Name $Name -Context $Context
    if ($null -eq $value -or $value -isnot [System.Array]) {
        throw "$Context property '$Name' must be an array"
    }
    $items = @($value)
    if (-not $AllowEmpty -and $items.Count -eq 0) {
        throw "$Context property '$Name' must be a non-empty array"
    }
    return $items
}

function Require-StringArray {
    param($Object, [string]$Name, [string]$Context, [switch]$AllowEmpty)
    $items = @(Require-Array -Object $Object -Name $Name -Context $Context -AllowEmpty:$AllowEmpty)
    for ($index = 0; $index -lt $items.Count; $index++) {
        if ($items[$index] -isnot [string] -or [string]::IsNullOrWhiteSpace($items[$index])) {
            throw "$Context property '$Name' item $index must be a non-empty string"
        }
    }
    return $items
}

function Require-Object {
    param($Object, [string]$Name, [string]$Context)
    $value = Require-Property -Object $Object -Name $Name -Context $Context
    if ($null -eq $value -or $value -isnot [System.Management.Automation.PSCustomObject]) {
        throw "$Context property '$Name' must be an object"
    }
    return $value
}

function Require-Boolean {
    param($Object, [string]$Name, [string]$Context)
    $value = Require-Property -Object $Object -Name $Name -Context $Context
    if ($value -isnot [bool]) { throw "$Context property '$Name' must be boolean" }
    return $value
}

function Assert-AllowedProperties {
    param($Object, [string[]]$Allowed, [string]$Context)
    if ($null -eq $Object -or $Object -isnot [System.Management.Automation.PSCustomObject]) {
        throw "$Context must be an object"
    }
    foreach ($propertyName in @($Object.PSObject.Properties.Name)) {
        if ($propertyName -notin $Allowed) {
            throw "$Context contains unsupported property '$propertyName'"
        }
    }
}

function New-OrdinalMap {
    return (New-Object System.Collections.Hashtable ([System.StringComparer]::Ordinal))
}

function Is-Number {
    param($Value)
    return ($Value -is [byte] -or $Value -is [sbyte] -or
            $Value -is [int16] -or $Value -is [uint16] -or
            $Value -is [int32] -or $Value -is [uint32] -or
            $Value -is [int64] -or $Value -is [uint64] -or
            $Value -is [single] -or $Value -is [double] -or
            $Value -is [decimal])
}

function Require-FiniteNumber {
    param($Value, [string]$Context)
    if (-not (Is-Number -Value $Value)) {
        throw "$Context must be numeric"
    }
    $number = [double]$Value
    if ([double]::IsNaN($number) -or [double]::IsInfinity($number)) {
        throw "$Context must be finite"
    }
    return $number
}

function Assert-NormalizedRequest {
    param($Value, [string]$Context)
    Assert-AllowedProperties -Object $Value -Allowed @('domain', 'target_users', 'idea_count', 'constraints') -Context $Context
    $domain = Require-String -Object $Value -Name 'domain' -Context $Context
    $targetUsers = @(Require-StringArray -Object $Value -Name 'target_users' -Context $Context)
    $ideaCount = Require-FiniteNumber -Value (Require-Property -Object $Value -Name 'idea_count' -Context $Context) -Context "$Context.idea_count"
    if ($ideaCount -lt 1 -or $ideaCount -ne [math]::Truncate($ideaCount)) { throw "$Context.idea_count must be a positive integer" }
    $constraints = Require-Object -Object $Value -Name 'constraints' -Context $Context
    Assert-AllowedProperties -Object $constraints -Allowed @('local_first', 'privacy_sensitive', 'target_platform', 'requirements') -Context "$Context.constraints"
    $localFirst = Require-Boolean -Object $constraints -Name 'local_first' -Context "$Context.constraints"
    $privacySensitive = Require-Boolean -Object $constraints -Name 'privacy_sensitive' -Context "$Context.constraints"
    $targetPlatform = Require-String -Object $constraints -Name 'target_platform' -Context "$Context.constraints"
    $requirements = @(Require-StringArray -Object $constraints -Name 'requirements' -Context "$Context.constraints" -AllowEmpty)
    return [pscustomobject][ordered]@{
        domain = $domain
        target_users = $targetUsers
        idea_count = [int]$ideaCount
        constraints = [pscustomobject][ordered]@{
            local_first = $localFirst
            privacy_sensitive = $privacySensitive
            target_platform = $targetPlatform
            requirements = $requirements
        }
    }
}

function Write-JsonAtomic {
    param($Value, [string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { throw 'OutputPath must be non-empty' }
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (Test-Path -LiteralPath $fullPath -PathType Container) {
        throw "OutputPath points to a directory: $fullPath"
    }
    $directory = [System.IO.Path]::GetDirectoryName($fullPath)
    if (-not [string]::IsNullOrWhiteSpace($directory) -and -not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $json = $Value | ConvertTo-Json -Depth 50
    $tempPath = "$fullPath.tmp.$PID.$([guid]::NewGuid().ToString('N'))"
    $encoding = New-Object System.Text.UTF8Encoding($false)
    try {
        [System.IO.File]::WriteAllText($tempPath, $json + [Environment]::NewLine, $encoding)
        Move-Item -LiteralPath $tempPath -Destination $fullPath -Force
    }
    finally {
        if (Test-Path -LiteralPath $tempPath) { Remove-Item -LiteralPath $tempPath -Force }
    }
}

function Assert-DistinctOutputPath {
    param([string]$Path, [string[]]$InputPaths)
    if ([string]::IsNullOrWhiteSpace($Path)) { throw 'OutputPath must be non-empty' }
    $fullOutputPath = [System.IO.Path]::GetFullPath($Path)
    foreach ($inputPath in $InputPaths) {
        $fullInputPath = [System.IO.Path]::GetFullPath($inputPath)
        if ([string]::Equals($fullOutputPath, $fullInputPath, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "OutputPath must not overwrite an input file: $fullInputPath"
        }
    }
}

function Assert-RunArtifactLayout {
    param([string]$RunId, $Artifacts)
    $runDirectory = $null
    foreach ($expectedName in @($Artifacts.Keys)) {
        $path = [string]$Artifacts[$expectedName]
        if ([string]::IsNullOrWhiteSpace($path)) { throw "Missing path for $expectedName" }
        $fullPath = [System.IO.Path]::GetFullPath($path)
        if (-not [string]::Equals([System.IO.Path]::GetFileName($fullPath), $expectedName, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Run artifact must be named '$expectedName': $fullPath"
        }
        $parent = [System.IO.Path]::GetDirectoryName($fullPath)
        if ($null -eq $runDirectory) {
            $runDirectory = $parent
        }
        elseif (-not [string]::Equals($runDirectory, $parent, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw 'Run artifacts must share one run directory'
        }
    }
    if (-not [string]::Equals([System.IO.Path]::GetFileName($runDirectory), $RunId, [System.StringComparison]::Ordinal)) {
        throw "Run directory name must equal run_id '$RunId': $runDirectory"
    }
    $runsDirectory = [System.IO.Path]::GetDirectoryName($runDirectory)
    if ([string]::IsNullOrWhiteSpace($runsDirectory) -or
        -not [string]::Equals([System.IO.Path]::GetFileName($runsDirectory), 'runs', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Run directory must be directly under a 'runs' directory: $runDirectory"
    }
}

Assert-DistinctOutputPath -Path $OutputPath -InputPaths @($RequestPath, $GenerationPath, $EvaluationInputPath, $EvaluationPath)
$request = Read-JsonFile -Path $RequestPath -Label 'request'
$generation = Read-JsonFile -Path $GenerationPath -Label 'generation'
$evaluationInput = Read-JsonFile -Path $EvaluationInputPath -Label 'evaluation-input'
$evaluation = Read-JsonFile -Path $EvaluationPath -Label 'evaluation'

Assert-AllowedProperties -Object $request -Allowed @('run_id', 'raw_request', 'normalized_request', 'weights') -Context 'request'
Assert-AllowedProperties -Object $generation -Allowed @('run_id', 'normalized_request', 'capability_chains', 'ideas', 'warnings') -Context 'generation'
Assert-AllowedProperties -Object $evaluationInput -Allowed @(
    'run_id', 'generation_sha256', 'evaluation_input_sha256', 'product_context', 'capability_chains', 'ideas', 'tools', 'rubric'
) -Context 'evaluation-input'
Assert-AllowedProperties -Object $evaluation -Allowed @('run_id', 'generation_sha256', 'evaluation_input_sha256', 'evaluations') -Context 'evaluation'

$requestRunId = Require-RunId -Object $request -Context 'request'
$generationRunId = Require-RunId -Object $generation -Context 'generation'
$evaluationInputRunId = Require-RunId -Object $evaluationInput -Context 'evaluation-input'
$evaluationRunId = Require-RunId -Object $evaluation -Context 'evaluation'
if ($requestRunId -cne $generationRunId -or $requestRunId -cne $evaluationInputRunId -or $requestRunId -cne $evaluationRunId) {
    throw "run_id mismatch across request, generation, evaluation-input, and evaluation"
}
Assert-RunArtifactLayout -RunId $requestRunId -Artifacts ([ordered]@{
    'request.json' = $RequestPath
    'generation.json' = $GenerationPath
    'evaluation-input.json' = $EvaluationInputPath
    'evaluation.json' = $EvaluationPath
    'result.json' = $OutputPath
})
$expectedGenerationHash = Get-FileSha256 -Path $GenerationPath
$inputGenerationHash = Require-Sha256 -Object $evaluationInput -Name 'generation_sha256' -Context 'evaluation-input'
$evaluationGenerationHash = Require-Sha256 -Object $evaluation -Name 'generation_sha256' -Context 'evaluation'
if ($inputGenerationHash -cne $expectedGenerationHash -or $evaluationGenerationHash -cne $expectedGenerationHash) {
    throw "generation_sha256 mismatch across generation, evaluation-input, and evaluation"
}
[void](Require-Object -Object $evaluationInput -Name 'product_context' -Context 'evaluation-input')
[void](Require-Array -Object $evaluationInput -Name 'capability_chains' -Context 'evaluation-input')
[void](Require-Array -Object $evaluationInput -Name 'ideas' -Context 'evaluation-input')
[void](Require-Array -Object $evaluationInput -Name 'tools' -Context 'evaluation-input')
[void](Require-Object -Object $evaluationInput -Name 'rubric' -Context 'evaluation-input')
$expectedInputHash = Get-ValueSha256 -Value (Get-EvaluationInputPayload -EvaluationInput $evaluationInput)
$inputHash = Require-Sha256 -Object $evaluationInput -Name 'evaluation_input_sha256' -Context 'evaluation-input'
$evaluationInputHash = Require-Sha256 -Object $evaluation -Name 'evaluation_input_sha256' -Context 'evaluation'
if ($inputHash -cne $expectedInputHash -or $evaluationInputHash -cne $expectedInputHash) {
    throw "evaluation_input_sha256 mismatch across evaluation-input and evaluation"
}
[void](Require-String -Object $request -Name 'raw_request' -Context 'request')
$normalizedRequestValue = Require-Object -Object $request -Name 'normalized_request' -Context 'request'
$generationNormalizedValue = Require-Object -Object $generation -Name 'normalized_request' -Context 'generation'
$normalizedRequest = Assert-NormalizedRequest -Value $normalizedRequestValue -Context 'request.normalized_request'
$generationNormalized = Assert-NormalizedRequest -Value $generationNormalizedValue -Context 'generation.normalized_request'
if (($normalizedRequest | ConvertTo-Json -Depth 10 -Compress) -cne ($generationNormalized | ConvertTo-Json -Depth 10 -Compress)) {
    throw 'generation.normalized_request must exactly copy request.normalized_request'
}

$weightsObject = Require-Object -Object $request -Name 'weights' -Context 'request'
$weightSum = 0.0
$rawWeights = [ordered]@{}
foreach ($dimension in $dimensions) {
    $weight = Require-Property -Object $weightsObject -Name $dimension -Context 'request weights'
    $weightNumber = Require-FiniteNumber -Value $weight -Context "Weight '$dimension'"
    if ($weightNumber -lt 0) {
        throw "Weight '$dimension' must be a non-negative number"
    }
    $rawWeights[$dimension] = $weightNumber
    $weightSum += $weightNumber
}
foreach ($propertyName in @($weightsObject.PSObject.Properties.Name)) {
    if ($propertyName -notin $dimensions) {
        throw "Unknown weight dimension: $propertyName"
    }
}
if ([double]::IsNaN($weightSum) -or [double]::IsInfinity($weightSum) -or $weightSum -le 0) {
    throw 'Weight sum must be finite and greater than zero'
}

$normalizedWeights = [ordered]@{}
foreach ($dimension in $dimensions) {
    $normalizedWeights[$dimension] = [double]$rawWeights[$dimension] / $weightSum
}

$chains = @(Require-Array -Object $generation -Name 'capability_chains' -Context 'generation')
$warnings = @(Require-StringArray -Object $generation -Name 'warnings' -Context 'generation' -AllowEmpty)
$chainMap = New-OrdinalMap
$chainToolMap = New-OrdinalMap
foreach ($chain in $chains) {
    Assert-AllowedProperties -Object $chain -Allowed @(
        'chain_id', 'domain', 'chain_summary', 'name', 'status', 'warnings', 'steps', 'capability_gaps'
    ) -Context 'capability_chain'
    $chainId = Require-Identifier -Object $chain -Name 'chain_id' -Context 'capability_chain'
    if ($chainMap.ContainsKey($chainId)) { throw "Duplicate chain_id: $chainId" }
    [void](Require-String -Object $chain -Name 'domain' -Context "chain '$chainId'")
    [void](Require-String -Object $chain -Name 'chain_summary' -Context "chain '$chainId'")
    if (Has-Property -Object $chain -Name 'name') {
        [void](Require-String -Object $chain -Name 'name' -Context "chain '$chainId'")
    }
    $status = (Require-String -Object $chain -Name 'status' -Context "chain '$chainId'").ToLowerInvariant()
    if ($status -notin @('complete', 'partial')) { throw "chain '$chainId' status must be complete or partial" }
    $chainWarnings = @(Require-StringArray -Object $chain -Name 'warnings' -Context "chain '$chainId'" -AllowEmpty)
    $chainGaps = @()
    if (Has-Property -Object $chain -Name 'capability_gaps') {
        $chainGaps = @(Require-StringArray -Object $chain -Name 'capability_gaps' -Context "chain '$chainId'" -AllowEmpty)
    }
    $steps = @(Require-Array -Object $chain -Name 'steps' -Context "chain '$chainId'")
    if ($steps.Count -gt 5) { throw "chain '$chainId' has more than 5 steps" }
    if ($status -eq 'complete' -and $steps.Count -lt 2) { throw "complete chain '$chainId' must contain 2 to 5 steps" }
    if ($status -eq 'complete' -and $chainGaps.Count -gt 0) {
        throw "complete chain '$chainId' must not declare capability_gaps"
    }
    if ($status -eq 'partial' -and $chainGaps.Count -eq 0) {
        throw "partial chain '$chainId' must declare at least one capability_gap"
    }
    $orders = New-OrdinalMap
    $chainToolIds = @()
    foreach ($step in $steps) {
        Assert-AllowedProperties -Object $step -Allowed @('order', 'tool_id', 'capability', 'input_types', 'output_types') -Context "step in chain '$chainId'"
        $orderValue = Require-Property -Object $step -Name 'order' -Context "step in chain '$chainId'"
        $orderNumber = Require-FiniteNumber -Value $orderValue -Context "step in chain '$chainId' order"
        if ($orderNumber -lt 1 -or $orderNumber -ne [math]::Truncate($orderNumber)) {
            throw "step in chain '$chainId' order must be a positive integer"
        }
        $orderKey = [string]([int]$orderNumber)
        if ($orders.ContainsKey($orderKey)) { throw "chain '$chainId' contains duplicate step order $orderKey" }
        $orders[$orderKey] = $true
        $toolId = Require-Identifier -Object $step -Name 'tool_id' -Context "step in chain '$chainId'"
        [void](Require-String -Object $step -Name 'capability' -Context "step in chain '$chainId'")
        [void](Require-StringArray -Object $step -Name 'input_types' -Context "step in chain '$chainId'")
        [void](Require-StringArray -Object $step -Name 'output_types' -Context "step in chain '$chainId'")
        $chainToolIds += $toolId
    }
    for ($expectedOrder = 1; $expectedOrder -le $steps.Count; $expectedOrder++) {
        if (-not $orders.ContainsKey([string]$expectedOrder)) {
            throw "chain '$chainId' step orders must be contiguous from 1 through $($steps.Count)"
        }
    }
    $chainMap[$chainId] = $chain
    $chainToolMap[$chainId] = @($chainToolIds)
}

$ideas = @(Require-Array -Object $generation -Name 'ideas' -Context 'generation')
$ideaMap = New-OrdinalMap
foreach ($idea in $ideas) {
    Assert-AllowedProperties -Object $idea -Allowed @(
        'idea_id', 'name', 'domain', 'target_user', 'problem', 'solution', 'user_flow',
        'capability_chain_ids', 'tool_ids', 'mvp_features', 'capability_gaps'
    ) -Context 'idea'
    $ideaId = Require-Identifier -Object $idea -Name 'idea_id' -Context 'idea'
    if ($ideaMap.ContainsKey($ideaId)) { throw "Duplicate idea_id: $ideaId" }
    foreach ($field in @('name', 'domain', 'target_user', 'problem', 'solution')) {
        [void](Require-String -Object $idea -Name $field -Context "idea '$ideaId'")
    }
    [void](Require-StringArray -Object $idea -Name 'user_flow' -Context "idea '$ideaId'")
    $ideaChainIds = @(Require-StringArray -Object $idea -Name 'capability_chain_ids' -Context "idea '$ideaId'")
    $ideaToolIds = @(Require-StringArray -Object $idea -Name 'tool_ids' -Context "idea '$ideaId'")
    [void](Require-StringArray -Object $idea -Name 'mvp_features' -Context "idea '$ideaId'")
    [void](Require-StringArray -Object $idea -Name 'capability_gaps' -Context "idea '$ideaId'" -AllowEmpty)
    $expectedTools = New-OrdinalMap
    $seenChains = New-OrdinalMap
    foreach ($chainId in $ideaChainIds) {
        if ($chainId -cne $chainId.Trim()) { throw "idea '$ideaId' chain_id must not contain surrounding whitespace: $chainId" }
        if ($seenChains.ContainsKey($chainId)) { throw "idea '$ideaId' contains duplicate chain_id: $chainId" }
        if (-not $chainMap.ContainsKey($chainId)) { throw "idea '$ideaId' references unknown chain_id: $chainId" }
        $seenChains[$chainId] = $true
        foreach ($toolId in @($chainToolMap[$chainId])) { $expectedTools[$toolId] = $true }
    }
    $seenTools = New-OrdinalMap
    foreach ($toolId in $ideaToolIds) {
        if ($toolId -cne $toolId.Trim()) { throw "idea '$ideaId' tool_id must not contain surrounding whitespace: $toolId" }
        if ($seenTools.ContainsKey($toolId)) { throw "idea '$ideaId' contains duplicate tool_id: $toolId" }
        if (-not $expectedTools.ContainsKey($toolId)) { throw "idea '$ideaId' tool_id is not present in its referenced chains: $toolId" }
        $seenTools[$toolId] = $true
    }
    foreach ($toolId in $expectedTools.Keys) {
        if (-not $seenTools.ContainsKey($toolId)) { throw "idea '$ideaId' omits tool_id from its referenced chains: $toolId" }
    }
    $ideaMap[$ideaId] = $idea
}

$evaluationItems = @(Require-Array -Object $evaluation -Name 'evaluations' -Context 'evaluation')
$evaluationMap = New-OrdinalMap
foreach ($item in $evaluationItems) {
    Assert-AllowedProperties -Object $item -Allowed @('idea_id', 'dimensions', 'risks') -Context 'evaluation item'
    $ideaId = Require-Identifier -Object $item -Name 'idea_id' -Context 'evaluation item'
    if (-not $ideaMap.ContainsKey($ideaId)) { throw "Evaluation references unknown idea_id: $ideaId" }
    if ($evaluationMap.ContainsKey($ideaId)) { throw "Duplicate evaluation for idea_id: $ideaId" }
    foreach ($forbidden in @('weights', 'total_score', 'rank', 'recommended')) {
        if (Has-Property -Object $item -Name $forbidden) { throw "evaluation '$ideaId' must not contain '$forbidden'" }
    }
    $dimensionObject = Require-Object -Object $item -Name 'dimensions' -Context "evaluation '$ideaId'"
    foreach ($dimension in $dimensions) {
        $detail = Require-Object -Object $dimensionObject -Name $dimension -Context "evaluation '$ideaId'"
        Assert-AllowedProperties -Object $detail -Allowed @('score', 'reason') -Context "evaluation '$ideaId' dimension '$dimension'"
        $score = Require-Property -Object $detail -Name 'score' -Context "evaluation '$ideaId' dimension '$dimension'"
        $scoreNumber = Require-FiniteNumber -Value $score -Context "evaluation '$ideaId' dimension '$dimension' score"
        if ($scoreNumber -lt 0 -or $scoreNumber -gt 100) {
            throw "evaluation '$ideaId' dimension '$dimension' score must be between 0 and 100"
        }
        [void](Require-String -Object $detail -Name 'reason' -Context "evaluation '$ideaId' dimension '$dimension'")
    }
    foreach ($propertyName in @($dimensionObject.PSObject.Properties.Name)) {
        if ($propertyName -notin $dimensions) { throw "evaluation '$ideaId' contains unknown dimension '$propertyName'" }
    }
    [void](Require-StringArray -Object $item -Name 'risks' -Context "evaluation '$ideaId'" -AllowEmpty)
    $evaluationMap[$ideaId] = $item
}
if ($evaluationMap.Count -ne $ideaMap.Count) {
    $missing = @($ideaMap.Keys | Where-Object { -not $evaluationMap.ContainsKey($_) })
    throw "Evaluation does not cover every idea. Missing: $($missing -join ', ')"
}

$rows = New-Object System.Collections.Generic.List[object]
foreach ($idea in $ideas) {
    $ideaId = [string]$idea.idea_id
    $item = $evaluationMap[$ideaId]
    $scores = [ordered]@{}
    $reasons = [ordered]@{}
    $total = 0.0
    foreach ($dimension in $dimensions) {
        $detail = $item.dimensions.PSObject.Properties[$dimension].Value
        $score = [double]$detail.score
        $scores[$dimension] = $score
        $reasons[$dimension] = [string]$detail.reason
        $total += $score * [double]$normalizedWeights[$dimension]
    }
    $rows.Add([pscustomobject][ordered]@{
        rank = 0
        recommended = $false
        total_score = [math]::Round($total, 2, [MidpointRounding]::AwayFromZero)
        idea = $idea
        scores = [pscustomobject]$scores
        reasons = [pscustomobject]$reasons
        risks = @($item.risks)
    })
}

[object[]]$sorted = $rows.ToArray()
$rowComparer = [System.Collections.Generic.Comparer[object]]::Create(
    [System.Comparison[object]]{
        param($left, $right)
        $comparison = [System.Collections.Generic.Comparer[double]]::Default.Compare([double]$right.total_score, [double]$left.total_score)
        if ($comparison -ne 0) { return $comparison }
        $comparison = [System.Collections.Generic.Comparer[double]]::Default.Compare([double]$right.scores.feasibility, [double]$left.scores.feasibility)
        if ($comparison -ne 0) { return $comparison }
        $comparison = [System.Collections.Generic.Comparer[double]]::Default.Compare([double]$right.scores.user_value, [double]$left.scores.user_value)
        if ($comparison -ne 0) { return $comparison }
        $comparison = [System.Collections.Generic.Comparer[double]]::Default.Compare([double]$right.scores.innovation, [double]$left.scores.innovation)
        if ($comparison -ne 0) { return $comparison }
        return [string]::Compare(
            [string]$left.idea.idea_id,
            [string]$right.idea.idea_id,
            [System.StringComparison]::Ordinal
        )
    }
)
[System.Array]::Sort($sorted, $rowComparer)

for ($index = 0; $index -lt $sorted.Count; $index++) {
    $sorted[$index].rank = $index + 1
    $sorted[$index].recommended = ($index -eq 0)
}

$result = [pscustomobject][ordered]@{
    run_id = $requestRunId
    status = 'success'
    normalized_request = $normalizedRequest
    weights = [pscustomobject]$normalizedWeights
    capability_chains = $chains
    ranking = $sorted
    recommended_idea_id = [string]$sorted[0].idea.idea_id
    warnings = $warnings
    errors = @()
}

Write-JsonAtomic -Value $result -Path $OutputPath

[pscustomobject][ordered]@{
    status = 'written'
    run_id = $requestRunId
    output_path = [System.IO.Path]::GetFullPath($OutputPath)
    ranked_count = $sorted.Count
    recommended_idea_id = [string]$sorted[0].idea.idea_id
} | ConvertTo-Json -Compress
