[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('ValidateCatalog', 'ValidateGeneration', 'BuildEvaluationInput', 'ValidateEvaluationInput', 'ValidateEvaluation')]
    [string]$Mode,

    [string]$CatalogPath,
    [string]$RequestPath,
    [string]$GenerationPath,
    [string]$EvaluationInputPath,
    [string]$EvaluationPath,
    [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:RunIdPattern = '^a2_[0-9]{8}_[0-9]{6}_[0-9a-f]{6}$'

$script:Dimensions = @(
    'user_value',
    'feasibility',
    'generality',
    'innovation',
    'visual_expression'
)

function Require-PathArgument {
    param([string]$Value, [string]$Name)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "Missing required parameter: $Name"
    }
}

function Read-JsonFile {
    param([string]$Path, [string]$Label)

    Require-PathArgument -Value $Path -Name $Label
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label not found: $Path"
    }

    try {
        $raw = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $Path).Path, [System.Text.Encoding]::UTF8)
        if ([string]::IsNullOrWhiteSpace($raw)) {
            throw 'file is empty'
        }
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
    Require-PathArgument -Value $Path -Name 'GenerationPath'
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "GenerationPath not found: $Path"
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
    if ($value -isnot [bool]) {
        throw "$Context property '$Name' must be boolean"
    }
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

function Assert-NoForbiddenContextKeys {
    param($Value, [string]$Context)
    if ($null -eq $Value) { return }
    if ($Value -is [System.Management.Automation.PSCustomObject]) {
        foreach ($property in $Value.PSObject.Properties) {
            $name = [string]$property.Name
            if ($name -match '(?i)^(raw(_request|_text)?|weights?|prompts?|reasoning|conversation|messages?|prior([_-].*)?)$') {
                throw "$Context contains forbidden context property '$name'"
            }
            Assert-NoForbiddenContextKeys -Value $property.Value -Context "$Context.$name"
        }
        return
    }
    if ($Value -is [System.Array]) {
        for ($index = 0; $index -lt $Value.Count; $index++) {
            Assert-NoForbiddenContextKeys -Value $Value[$index] -Context "$Context[$index]"
        }
    }
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

function Write-JsonAtomic {
    param($Value, [string]$Path)

    Require-PathArgument -Value $Path -Name 'OutputPath'
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
        if (Test-Path -LiteralPath $tempPath) {
            Remove-Item -LiteralPath $tempPath -Force
        }
    }
}

function Assert-DistinctOutputPath {
    param([string]$Path, [string[]]$InputPaths)
    Require-PathArgument -Value $Path -Name 'OutputPath'
    $fullOutputPath = [System.IO.Path]::GetFullPath($Path)
    foreach ($inputPath in $InputPaths) {
        if ([string]::IsNullOrWhiteSpace($inputPath)) { continue }
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
        Require-PathArgument -Value $path -Name $expectedName
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

function Get-CatalogState {
    param($Catalog)

    $records = @($Catalog)
    if ($records.Count -eq 0) {
        throw 'Catalog must contain at least one record'
    }

    $activeMap = New-OrdinalMap
    $skipped = 0
    foreach ($record in $records) {
        $status = ''
        if ((Has-Property -Object $record -Name 'meta') -and $null -ne $record.meta -and
            (Has-Property -Object $record.meta -Name 'status')) {
            $status = ([string]$record.meta.status).Trim().ToLowerInvariant()
        }
        if ($status -ne 'active') {
            $skipped++
            continue
        }

        if (-not (Has-Property -Object $record -Name 'id') -or
            -not (Has-Property -Object $record -Name 'description') -or
            $record.id -isnot [string] -or
            $record.description -isnot [string] -or
            [string]::IsNullOrWhiteSpace([string]$record.id) -or
            [string]::IsNullOrWhiteSpace([string]$record.description) -or
            $record.id -cne $record.id.Trim()) {
            $skipped++
            continue
        }

        $id = [string]$record.id
        if ($activeMap.ContainsKey($id)) {
            throw "Catalog contains duplicate active id: $id"
        }
        $activeMap[$id] = $record
    }

    if ($activeMap.Count -eq 0) {
        throw 'Catalog has no active records with non-empty id and description'
    }

    return [pscustomobject][ordered]@{
        records = $records
        active_map = $activeMap
        active_count = $activeMap.Count
        skipped_count = $skipped
    }
}

function Assert-RunIdMatch {
    param($Left, $Right, [string]$LeftLabel, [string]$RightLabel)
    $leftId = Require-RunId -Object $Left -Context $LeftLabel
    $rightId = Require-RunId -Object $Right -Context $RightLabel
    if ($leftId -cne $rightId) {
        throw "run_id mismatch: $LeftLabel=$leftId, $RightLabel=$rightId"
    }
    return $leftId
}

function Assert-NormalizedRequest {
    param($NormalizedRequest, [string]$Context)

    Assert-AllowedProperties -Object $NormalizedRequest -Allowed @('domain', 'target_users', 'idea_count', 'constraints') -Context $Context
    $domain = Require-String -Object $NormalizedRequest -Name 'domain' -Context $Context
    $targetUsers = @(Require-StringArray -Object $NormalizedRequest -Name 'target_users' -Context $Context)
    $ideaCount = Require-FiniteNumber -Value (Require-Property -Object $NormalizedRequest -Name 'idea_count' -Context $Context) -Context "$Context.idea_count"
    if ($ideaCount -lt 1 -or $ideaCount -ne [math]::Truncate($ideaCount)) {
        throw "$Context.idea_count must be a positive integer"
    }

    $constraints = Require-Object -Object $NormalizedRequest -Name 'constraints' -Context $Context
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

function Assert-NormalizedRequestMatch {
    param($Expected, $Actual)
    if ($Expected.domain -cne $Actual.domain -or $Expected.idea_count -ne $Actual.idea_count) {
        throw 'generation.normalized_request must exactly copy request.normalized_request'
    }
    foreach ($field in @('target_users')) {
        $left = @($Expected.$field)
        $right = @($Actual.$field)
        if ($left.Count -ne $right.Count) { throw 'generation.normalized_request must exactly copy request.normalized_request' }
        for ($index = 0; $index -lt $left.Count; $index++) {
            if ($left[$index] -cne $right[$index]) { throw 'generation.normalized_request must exactly copy request.normalized_request' }
        }
    }
    foreach ($field in @('local_first', 'privacy_sensitive', 'target_platform')) {
        if ($Expected.constraints.$field -cne $Actual.constraints.$field) {
            throw 'generation.normalized_request must exactly copy request.normalized_request'
        }
    }
    $leftRequirements = @($Expected.constraints.requirements)
    $rightRequirements = @($Actual.constraints.requirements)
    if ($leftRequirements.Count -ne $rightRequirements.Count) { throw 'generation.normalized_request must exactly copy request.normalized_request' }
    for ($index = 0; $index -lt $leftRequirements.Count; $index++) {
        if ($leftRequirements[$index] -cne $rightRequirements[$index]) { throw 'generation.normalized_request must exactly copy request.normalized_request' }
    }
}

function Assert-Request {
    param($Request)

    Assert-AllowedProperties -Object $Request -Allowed @('run_id', 'raw_request', 'normalized_request', 'weights') -Context 'request'
    $runId = Require-RunId -Object $Request -Context 'request'
    [void](Require-String -Object $Request -Name 'raw_request' -Context 'request')
    $normalizedRequestValue = Require-Object -Object $Request -Name 'normalized_request' -Context 'request'
    $normalizedRequest = Assert-NormalizedRequest -NormalizedRequest $normalizedRequestValue -Context 'request.normalized_request'
    Assert-NoForbiddenContextKeys -Value $normalizedRequest -Context 'request.normalized_request'

    $weights = Require-Object -Object $Request -Name 'weights' -Context 'request'
    Assert-AllowedProperties -Object $weights -Allowed $script:Dimensions -Context 'request.weights'
    $weightSum = 0.0
    foreach ($dimension in $script:Dimensions) {
        $weight = Require-Property -Object $weights -Name $dimension -Context 'request.weights'
        $number = Require-FiniteNumber -Value $weight -Context "request.weights.$dimension"
        if ($number -lt 0) {
            throw "request.weights.$dimension must be non-negative"
        }
        $weightSum += $number
    }
    if ([double]::IsNaN($weightSum) -or [double]::IsInfinity($weightSum) -or $weightSum -le 0) {
        throw 'request.weights sum must be finite and greater than zero'
    }

    return [pscustomobject][ordered]@{
        run_id = $runId
        normalized_request = $normalizedRequest
    }
}

function Assert-Generation {
    param($Generation, $Request, $CatalogState)

    Assert-AllowedProperties -Object $Generation -Allowed @('run_id', 'normalized_request', 'capability_chains', 'ideas', 'warnings') -Context 'generation'
    $runId = Require-RunId -Object $Generation -Context 'generation'
    $generationNormalizedValue = Require-Object -Object $Generation -Name 'normalized_request' -Context 'generation'
    $generationNormalized = Assert-NormalizedRequest -NormalizedRequest $generationNormalizedValue -Context 'generation.normalized_request'
    if ($null -ne $Request) {
        $requestValidation = Assert-Request -Request $Request
        [void](Assert-RunIdMatch -Left $Request -Right $Generation -LeftLabel 'request' -RightLabel 'generation')
        Assert-NormalizedRequestMatch -Expected $requestValidation.normalized_request -Actual $generationNormalized
    }
    [void](Require-StringArray -Object $Generation -Name 'warnings' -Context 'generation' -AllowEmpty)

    $chains = @(Require-Array -Object $Generation -Name 'capability_chains' -Context 'generation')
    $ideas = @(Require-Array -Object $Generation -Name 'ideas' -Context 'generation')
    $chainMap = New-OrdinalMap
    $chainToolMap = New-OrdinalMap

    foreach ($chain in $chains) {
        Assert-AllowedProperties -Object $chain -Allowed @(
            'chain_id', 'domain', 'chain_summary', 'name', 'status', 'warnings', 'steps', 'capability_gaps'
        ) -Context 'capability_chain'
        $chainId = Require-Identifier -Object $chain -Name 'chain_id' -Context 'capability_chain'
        if ($chainMap.ContainsKey($chainId)) {
            throw "Duplicate chain_id: $chainId"
        }
        [void](Require-String -Object $chain -Name 'domain' -Context "chain '$chainId'")
        [void](Require-String -Object $chain -Name 'chain_summary' -Context "chain '$chainId'")
        if (Has-Property -Object $chain -Name 'name') {
            [void](Require-String -Object $chain -Name 'name' -Context "chain '$chainId'")
        }
        $status = (Require-String -Object $chain -Name 'status' -Context "chain '$chainId'").ToLowerInvariant()
        if ($status -notin @('complete', 'partial')) {
            throw "chain '$chainId' status must be complete or partial"
        }
        $warnings = @(Require-StringArray -Object $chain -Name 'warnings' -Context "chain '$chainId'" -AllowEmpty)
        $gaps = @()
        if (Has-Property -Object $chain -Name 'capability_gaps') {
            $gaps = @(Require-StringArray -Object $chain -Name 'capability_gaps' -Context "chain '$chainId'" -AllowEmpty)
        }
        $steps = @(Require-Array -Object $chain -Name 'steps' -Context "chain '$chainId'")
        if ($steps.Count -gt 5) {
            throw "chain '$chainId' has more than 5 steps"
        }
        if ($status -eq 'complete' -and $steps.Count -lt 2) {
            throw "complete chain '$chainId' must contain 2 to 5 steps"
        }
        if ($status -eq 'complete' -and $gaps.Count -gt 0) {
            throw "complete chain '$chainId' must not declare capability_gaps"
        }
        if ($status -eq 'partial' -and $gaps.Count -eq 0) {
            throw "partial chain '$chainId' must declare at least one capability_gap"
        }

        $orders = New-OrdinalMap
        $toolIds = @()
        foreach ($step in $steps) {
            $context = "step in chain '$chainId'"
            Assert-AllowedProperties -Object $step -Allowed @('order', 'tool_id', 'capability', 'input_types', 'output_types') -Context $context
            $order = Require-Property -Object $step -Name 'order' -Context $context
            $orderNumber = Require-FiniteNumber -Value $order -Context "$context order"
            if ($orderNumber -lt 1 -or $orderNumber -ne [math]::Truncate($orderNumber)) {
                throw "$context order must be a positive integer"
            }
            $orderKey = [string]([int]$orderNumber)
            if ($orders.ContainsKey($orderKey)) {
                throw "chain '$chainId' contains duplicate step order $orderKey"
            }
            $orders[$orderKey] = $true

            $toolId = Require-Identifier -Object $step -Name 'tool_id' -Context $context
            if (-not $CatalogState.active_map.ContainsKey($toolId)) {
                throw "chain '$chainId' references unknown or inactive tool_id: $toolId"
            }
            [void](Require-String -Object $step -Name 'capability' -Context $context)
            [void](Require-StringArray -Object $step -Name 'input_types' -Context $context)
            [void](Require-StringArray -Object $step -Name 'output_types' -Context $context)
            $toolIds += $toolId
        }
        for ($expectedOrder = 1; $expectedOrder -le $steps.Count; $expectedOrder++) {
            if (-not $orders.ContainsKey([string]$expectedOrder)) {
                throw "chain '$chainId' step orders must be contiguous from 1 through $($steps.Count)"
            }
        }

        $chainMap[$chainId] = $chain
        $chainToolMap[$chainId] = @($toolIds)
    }

    $ideaMap = New-OrdinalMap
    $referencedChainIds = New-OrdinalMap
    foreach ($idea in $ideas) {
        Assert-AllowedProperties -Object $idea -Allowed @(
            'idea_id', 'name', 'domain', 'target_user', 'problem', 'solution', 'user_flow',
            'capability_chain_ids', 'tool_ids', 'mvp_features', 'capability_gaps'
        ) -Context 'idea'
        $ideaId = Require-Identifier -Object $idea -Name 'idea_id' -Context 'idea'
        if ($ideaMap.ContainsKey($ideaId)) {
            throw "Duplicate idea_id: $ideaId"
        }
        foreach ($field in @('name', 'domain', 'target_user', 'problem', 'solution')) {
            [void](Require-String -Object $idea -Name $field -Context "idea '$ideaId'")
        }
        [void](Require-StringArray -Object $idea -Name 'user_flow' -Context "idea '$ideaId'")
        [void](Require-StringArray -Object $idea -Name 'mvp_features' -Context "idea '$ideaId'")
        $chainIds = @(Require-StringArray -Object $idea -Name 'capability_chain_ids' -Context "idea '$ideaId'")
        $toolIds = @(Require-StringArray -Object $idea -Name 'tool_ids' -Context "idea '$ideaId'")
        [void](Require-StringArray -Object $idea -Name 'capability_gaps' -Context "idea '$ideaId'" -AllowEmpty)

        $referencedTools = New-OrdinalMap
        $seenIdeaChains = New-OrdinalMap
        foreach ($chainIdValue in $chainIds) {
            $chainId = $chainIdValue
            if ($chainId -cne $chainId.Trim()) {
                throw "idea '$ideaId' chain_id must not contain surrounding whitespace: $chainId"
            }
            if ($seenIdeaChains.ContainsKey($chainId)) {
                throw "idea '$ideaId' contains duplicate chain_id: $chainId"
            }
            if (-not $chainMap.ContainsKey($chainId)) {
                throw "idea '$ideaId' references unknown chain_id: $chainId"
            }
            $seenIdeaChains[$chainId] = $true
            $referencedChainIds[$chainId] = $true
            foreach ($chainTool in @($chainToolMap[$chainId])) {
                $referencedTools[$chainTool] = $true
            }
        }
        $seenIdeaTools = New-OrdinalMap
        foreach ($toolIdValue in $toolIds) {
            $toolId = $toolIdValue
            if ($toolId -cne $toolId.Trim()) {
                throw "idea '$ideaId' tool_id must not contain surrounding whitespace: $toolId"
            }
            if ($seenIdeaTools.ContainsKey($toolId)) {
                throw "idea '$ideaId' contains duplicate tool_id: $toolId"
            }
            $seenIdeaTools[$toolId] = $true
            if (-not $CatalogState.active_map.ContainsKey($toolId)) {
                throw "idea '$ideaId' references unknown or inactive tool_id: $toolId"
            }
            if (-not $referencedTools.ContainsKey($toolId)) {
                throw "idea '$ideaId' tool_id is not present in its referenced chains: $toolId"
            }
        }
        foreach ($referencedToolId in $referencedTools.Keys) {
            if (-not $seenIdeaTools.ContainsKey($referencedToolId)) {
                throw "idea '$ideaId' omits tool_id from its referenced chains: $referencedToolId"
            }
        }
        $ideaMap[$ideaId] = $idea
    }

    $referencedChains = @($chains | Where-Object { $referencedChainIds.ContainsKey([string]$_.chain_id) })

    return [pscustomobject][ordered]@{
        run_id = $runId
        chain_count = $chains.Count
        idea_count = $ideas.Count
        chains = $chains
        ideas = $ideas
        referenced_chains = $referencedChains
        chain_map = $chainMap
        idea_map = $ideaMap
    }
}

function Assert-Evaluation {
    param($Generation, $EvaluationInput, $Evaluation, [string]$GenerationPath)

    $inputValidation = Assert-EvaluationInputMatchesGeneration -EvaluationInput $EvaluationInput -Generation $Generation -GenerationPath $GenerationPath
    Assert-AllowedProperties -Object $Evaluation -Allowed @('run_id', 'generation_sha256', 'evaluation_input_sha256', 'evaluations') -Context 'evaluation'
    $runId = Assert-RunIdMatch -Left $Generation -Right $Evaluation -LeftLabel 'generation' -RightLabel 'evaluation'
    $expectedHash = $inputValidation.generation_sha256
    $actualHash = Require-Sha256 -Object $Evaluation -Name 'generation_sha256' -Context 'evaluation'
    if ($actualHash -cne $expectedHash) {
        throw "evaluation generation_sha256 mismatch: expected $expectedHash, got $actualHash"
    }
    $actualInputHash = Require-Sha256 -Object $Evaluation -Name 'evaluation_input_sha256' -Context 'evaluation'
    if ($actualInputHash -cne $inputValidation.evaluation_input_sha256) {
        throw "evaluation evaluation_input_sha256 mismatch: expected $($inputValidation.evaluation_input_sha256), got $actualInputHash"
    }
    $ideas = @(Require-Array -Object $Generation -Name 'ideas' -Context 'generation')
    $evaluations = @(Require-Array -Object $Evaluation -Name 'evaluations' -Context 'evaluation')

    $ideaIds = New-OrdinalMap
    foreach ($idea in $ideas) {
        $ideaId = Require-Identifier -Object $idea -Name 'idea_id' -Context 'idea'
        if ($ideaIds.ContainsKey($ideaId)) {
            throw "Duplicate generation idea_id: $ideaId"
        }
        $ideaIds[$ideaId] = $true
    }

    $evaluationIds = New-OrdinalMap
    foreach ($item in $evaluations) {
        Assert-AllowedProperties -Object $item -Allowed @('idea_id', 'dimensions', 'risks') -Context 'evaluation item'
        $ideaId = Require-Identifier -Object $item -Name 'idea_id' -Context 'evaluation item'
        if ($evaluationIds.ContainsKey($ideaId)) {
            throw "Duplicate evaluation for idea_id: $ideaId"
        }
        if (-not $ideaIds.ContainsKey($ideaId)) {
            throw "Evaluation references unknown idea_id: $ideaId"
        }
        foreach ($forbidden in @('weights', 'total_score', 'rank', 'recommended')) {
            if (Has-Property -Object $item -Name $forbidden) {
                throw "evaluation '$ideaId' must not contain '$forbidden'"
            }
        }

        $dimensions = Require-Object -Object $item -Name 'dimensions' -Context "evaluation '$ideaId'"
        $dimensionNames = @($dimensions.PSObject.Properties.Name)
        foreach ($dimension in $script:Dimensions) {
            if (-not (Has-Property -Object $dimensions -Name $dimension)) {
                throw "evaluation '$ideaId' is missing dimension '$dimension'"
            }
            $detail = $dimensions.PSObject.Properties[$dimension].Value
            if ($null -eq $detail -or $detail -isnot [System.Management.Automation.PSCustomObject]) {
                throw "evaluation '$ideaId' dimension '$dimension' must be an object"
            }
            Assert-AllowedProperties -Object $detail -Allowed @('score', 'reason') -Context "evaluation '$ideaId' dimension '$dimension'"
            $score = Require-Property -Object $detail -Name 'score' -Context "evaluation '$ideaId' dimension '$dimension'"
            $scoreNumber = Require-FiniteNumber -Value $score -Context "evaluation '$ideaId' dimension '$dimension' score"
            if ($scoreNumber -lt 0 -or $scoreNumber -gt 100) {
                throw "evaluation '$ideaId' dimension '$dimension' score must be between 0 and 100"
            }
            [void](Require-String -Object $detail -Name 'reason' -Context "evaluation '$ideaId' dimension '$dimension'")
        }
        foreach ($dimensionName in $dimensionNames) {
            if ($dimensionName -notin $script:Dimensions) {
                throw "evaluation '$ideaId' contains unknown dimension '$dimensionName'"
            }
        }
        [void](Require-StringArray -Object $item -Name 'risks' -Context "evaluation '$ideaId'" -AllowEmpty)
        $evaluationIds[$ideaId] = $true
    }

    if ($evaluationIds.Count -ne $ideaIds.Count) {
        $missing = @($ideaIds.Keys | Where-Object { -not $evaluationIds.ContainsKey($_) })
        throw "Evaluation does not cover every idea. Missing: $($missing -join ', ')"
    }

    foreach ($forbidden in @('weights', 'total_score', 'ranking', 'recommended_idea_id')) {
        if (Has-Property -Object $Evaluation -Name $forbidden) {
            throw "evaluation must not contain '$forbidden'"
        }
    }

    return [pscustomobject][ordered]@{
        run_id = $runId
        idea_count = $ideaIds.Count
        evaluation_count = $evaluationIds.Count
    }
}

function Copy-SanitizedProductContext {
    param($NormalizedRequest)

    $result = [ordered]@{}
    if ($null -eq $NormalizedRequest) {
        return [pscustomobject]$result
    }
    foreach ($property in $NormalizedRequest.PSObject.Properties) {
        $name = [string]$property.Name
        if ($name -match '(?i)^(raw(_request|_text)?|weights?|prompts?|reasoning|conversation|messages?|prior([_-].*)?)$') {
            continue
        }
        $result[$name] = $property.Value
    }
    return [pscustomobject]$result
}

function New-EvaluationRubric {
    return [pscustomobject][ordered]@{
        user_value = 'Practical value of the problem and solution for the target user.'
        feasibility = 'Coverage by CLI capabilities, compatibility, MVP scope, and gaps.'
        generality = 'Ability to extend to more users, workflows, or adjacent domains.'
        innovation = 'Novelty of the capability combination and product interaction.'
        visual_expression = 'How directly the input, transformation, and result can be demonstrated.'
    }
}

function ConvertTo-ComparableJson {
    param($Value)
    return (ConvertTo-Json -InputObject $Value -Depth 50 -Compress)
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

function Assert-EvaluationInputMatchesGeneration {
    param($EvaluationInput, $Generation, [string]$GenerationPath)

    Assert-AllowedProperties -Object $Generation -Allowed @('run_id', 'normalized_request', 'capability_chains', 'ideas', 'warnings') -Context 'generation'
    Assert-AllowedProperties -Object $EvaluationInput -Allowed @(
        'run_id', 'generation_sha256', 'evaluation_input_sha256', 'product_context', 'capability_chains', 'ideas', 'tools', 'rubric'
    ) -Context 'evaluation-input'
    $runId = Assert-RunIdMatch -Left $Generation -Right $EvaluationInput -LeftLabel 'generation' -RightLabel 'evaluation-input'
    $expectedHash = Get-FileSha256 -Path $GenerationPath
    $actualHash = Require-Sha256 -Object $EvaluationInput -Name 'generation_sha256' -Context 'evaluation-input'
    if ($actualHash -cne $expectedHash) {
        throw "evaluation-input generation_sha256 mismatch: expected $expectedHash, got $actualHash"
    }

    $normalizedRequest = Require-Object -Object $Generation -Name 'normalized_request' -Context 'generation'
    $productContext = Require-Object -Object $EvaluationInput -Name 'product_context' -Context 'evaluation-input'
    $expectedContext = Copy-SanitizedProductContext -NormalizedRequest $normalizedRequest
    if ((ConvertTo-ComparableJson -Value $productContext) -cne (ConvertTo-ComparableJson -Value $expectedContext)) {
        throw 'evaluation-input product_context does not match generation.normalized_request'
    }

    $generationIdeas = @(Require-Array -Object $Generation -Name 'ideas' -Context 'generation')
    $inputIdeas = @(Require-Array -Object $EvaluationInput -Name 'ideas' -Context 'evaluation-input')
    if ((ConvertTo-ComparableJson -Value $inputIdeas) -cne (ConvertTo-ComparableJson -Value $generationIdeas)) {
        throw 'evaluation-input ideas do not match generation'
    }

    $referencedChainIds = New-OrdinalMap
    foreach ($idea in $generationIdeas) {
        foreach ($chainId in @(Require-StringArray -Object $idea -Name 'capability_chain_ids' -Context 'generation idea')) {
            $referencedChainIds[$chainId] = $true
        }
    }
    $generationChains = @(Require-Array -Object $Generation -Name 'capability_chains' -Context 'generation')
    $expectedChains = @($generationChains | Where-Object { $referencedChainIds.ContainsKey([string]$_.chain_id) })
    $inputChains = @(Require-Array -Object $EvaluationInput -Name 'capability_chains' -Context 'evaluation-input')
    if ((ConvertTo-ComparableJson -Value $inputChains) -cne (ConvertTo-ComparableJson -Value $expectedChains)) {
        throw 'evaluation-input capability_chains do not match generation references'
    }

    [void](Require-Array -Object $EvaluationInput -Name 'tools' -Context 'evaluation-input')
    $rubric = Require-Object -Object $EvaluationInput -Name 'rubric' -Context 'evaluation-input'
    Assert-AllowedProperties -Object $rubric -Allowed $script:Dimensions -Context 'evaluation-input.rubric'
    $expectedRubric = New-EvaluationRubric
    foreach ($dimension in $script:Dimensions) {
        $rubricValue = Require-String -Object $rubric -Name $dimension -Context 'evaluation-input.rubric'
        if ($rubricValue -cne [string]$expectedRubric.$dimension) {
            throw "evaluation-input rubric '$dimension' does not match the A2 rubric"
        }
    }
    Assert-NoForbiddenContextKeys -Value $EvaluationInput -Context 'evaluation-input'
    $actualInputHash = Require-Sha256 -Object $EvaluationInput -Name 'evaluation_input_sha256' -Context 'evaluation-input'
    $expectedInputHash = Get-ValueSha256 -Value (Get-EvaluationInputPayload -EvaluationInput $EvaluationInput)
    if ($actualInputHash -cne $expectedInputHash) {
        throw "evaluation-input evaluation_input_sha256 mismatch: expected $expectedInputHash, got $actualInputHash"
    }

    return [pscustomobject][ordered]@{
        run_id = $runId
        generation_sha256 = $actualHash
        evaluation_input_sha256 = $actualInputHash
        idea_count = $inputIdeas.Count
        chain_count = $inputChains.Count
    }
}

switch ($Mode) {
    'ValidateCatalog' {
        $catalog = Read-JsonFile -Path $CatalogPath -Label 'CatalogPath'
        $state = Get-CatalogState -Catalog $catalog
        [pscustomobject][ordered]@{
            status = 'valid'
            mode = $Mode
            active_count = $state.active_count
            skipped_count = $state.skipped_count
        } | ConvertTo-Json -Compress
    }

    'ValidateGeneration' {
        $catalog = Read-JsonFile -Path $CatalogPath -Label 'CatalogPath'
        $request = Read-JsonFile -Path $RequestPath -Label 'RequestPath'
        $generation = Read-JsonFile -Path $GenerationPath -Label 'GenerationPath'
        $state = Get-CatalogState -Catalog $catalog
        $validation = Assert-Generation -Generation $generation -Request $request -CatalogState $state
        Assert-RunArtifactLayout -RunId $validation.run_id -Artifacts ([ordered]@{
            'request.json' = $RequestPath
            'generation.json' = $GenerationPath
        })
        [pscustomobject][ordered]@{
            status = 'valid'
            mode = $Mode
            run_id = $validation.run_id
            chain_count = $validation.chain_count
            idea_count = $validation.idea_count
        } | ConvertTo-Json -Compress
    }

    'BuildEvaluationInput' {
        Assert-DistinctOutputPath -Path $OutputPath -InputPaths @($CatalogPath, $RequestPath, $GenerationPath)
        $catalog = Read-JsonFile -Path $CatalogPath -Label 'CatalogPath'
        $request = Read-JsonFile -Path $RequestPath -Label 'RequestPath'
        $generation = Read-JsonFile -Path $GenerationPath -Label 'GenerationPath'
        $state = Get-CatalogState -Catalog $catalog
        $validation = Assert-Generation -Generation $generation -Request $request -CatalogState $state
        Assert-RunArtifactLayout -RunId $validation.run_id -Artifacts ([ordered]@{
            'request.json' = $RequestPath
            'generation.json' = $GenerationPath
            'evaluation-input.json' = $OutputPath
        })

        $usedToolIds = New-OrdinalMap
        foreach ($chain in @($validation.referenced_chains)) {
            foreach ($step in @($chain.steps)) {
                $usedToolIds[([string]$step.tool_id).Trim()] = $true
            }
        }
        $toolSummaries = @()
        foreach ($toolId in @($usedToolIds.Keys | Sort-Object)) {
            $record = $state.active_map[$toolId]
            $agentSummary = [ordered]@{}
            if ((Has-Property -Object $record -Name 'agent') -and $null -ne $record.agent) {
                if (Has-Property -Object $record.agent -Name 'score') { $agentSummary['score'] = $record.agent.score }
                if (Has-Property -Object $record.agent -Name 'friendly') { $agentSummary['friendly'] = $record.agent.friendly }
            }
            $toolSummaries += [pscustomobject][ordered]@{
                id = $toolId
                name = if (Has-Property -Object $record -Name 'name') { [string]$record.name } else { $toolId }
                description = [string]$record.description
                category = if (Has-Property -Object $record -Name 'category') { [string]$record.category } else { '' }
                tags = if (Has-Property -Object $record -Name 'tags') { @($record.tags) } else { @() }
                agent = [pscustomobject]$agentSummary
            }
        }

        $rubric = New-EvaluationRubric
        $evaluationPayload = [pscustomobject][ordered]@{
            run_id = $validation.run_id
            generation_sha256 = (Get-FileSha256 -Path $GenerationPath)
            product_context = (Copy-SanitizedProductContext -NormalizedRequest $generation.normalized_request)
            capability_chains = @($validation.referenced_chains)
            ideas = @($validation.ideas)
            tools = @($toolSummaries)
            rubric = $rubric
        }
        $evaluationInputHash = Get-ValueSha256 -Value $evaluationPayload
        $evaluationInput = [pscustomobject][ordered]@{
            run_id = $evaluationPayload.run_id
            generation_sha256 = $evaluationPayload.generation_sha256
            evaluation_input_sha256 = $evaluationInputHash
            product_context = $evaluationPayload.product_context
            capability_chains = @($evaluationPayload.capability_chains)
            ideas = @($evaluationPayload.ideas)
            tools = @($evaluationPayload.tools)
            rubric = $evaluationPayload.rubric
        }
        Write-JsonAtomic -Value $evaluationInput -Path $OutputPath

        [pscustomobject][ordered]@{
            status = 'written'
            mode = $Mode
            run_id = $validation.run_id
            output_path = [System.IO.Path]::GetFullPath($OutputPath)
            evaluation_input_sha256 = $evaluationInputHash
            idea_count = $validation.idea_count
            tool_count = $toolSummaries.Count
        } | ConvertTo-Json -Compress
    }

    'ValidateEvaluationInput' {
        $generation = Read-JsonFile -Path $GenerationPath -Label 'GenerationPath'
        $evaluationInput = Read-JsonFile -Path $EvaluationInputPath -Label 'EvaluationInputPath'
        $validation = Assert-EvaluationInputMatchesGeneration -EvaluationInput $evaluationInput -Generation $generation -GenerationPath $GenerationPath
        Assert-RunArtifactLayout -RunId $validation.run_id -Artifacts ([ordered]@{
            'generation.json' = $GenerationPath
            'evaluation-input.json' = $EvaluationInputPath
        })
        [pscustomobject][ordered]@{
            status = 'valid'
            mode = $Mode
            run_id = $validation.run_id
            generation_sha256 = $validation.generation_sha256
            evaluation_input_sha256 = $validation.evaluation_input_sha256
            idea_count = $validation.idea_count
            chain_count = $validation.chain_count
        } | ConvertTo-Json -Compress
    }

    'ValidateEvaluation' {
        $generation = Read-JsonFile -Path $GenerationPath -Label 'GenerationPath'
        $evaluationInput = Read-JsonFile -Path $EvaluationInputPath -Label 'EvaluationInputPath'
        $evaluation = Read-JsonFile -Path $EvaluationPath -Label 'EvaluationPath'
        $validation = Assert-Evaluation -Generation $generation -EvaluationInput $evaluationInput -Evaluation $evaluation -GenerationPath $GenerationPath
        Assert-RunArtifactLayout -RunId $validation.run_id -Artifacts ([ordered]@{
            'generation.json' = $GenerationPath
            'evaluation-input.json' = $EvaluationInputPath
            'evaluation.json' = $EvaluationPath
        })
        [pscustomobject][ordered]@{
            status = 'valid'
            mode = $Mode
            run_id = $validation.run_id
            evaluation_count = $validation.evaluation_count
        } | ConvertTo-Json -Compress
    }
}
