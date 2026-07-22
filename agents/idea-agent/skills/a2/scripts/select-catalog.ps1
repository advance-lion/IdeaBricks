[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('ListCategories', 'BuildSlice')]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$CatalogRoot,

    [string]$QueryPath,
    [string]$OutputPath,
    [string]$MetadataPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:RunIdPattern = '^a2_[0-9]{8}_[0-9]{6}_[0-9a-f]{6}$'

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

function Write-JsonAtomic {
    param($Value, [string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { throw 'Output path must be non-empty' }
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (Test-Path -LiteralPath $fullPath -PathType Container) {
        throw "Output path points to a directory: $fullPath"
    }
    $directory = [System.IO.Path]::GetDirectoryName($fullPath)
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $json = ConvertTo-Json -InputObject $Value -Depth 50
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

function Has-Property {
    param($Object, [string]$Name)
    return ($null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name])
}

function Require-StringArray {
    param($Object, [string]$Name, [switch]$AllowEmpty)
    if (-not (Has-Property -Object $Object -Name $Name)) {
        throw "Query is missing property '$Name'"
    }
    $value = $Object.PSObject.Properties[$Name].Value
    if ($null -eq $value -or $value -isnot [System.Array]) {
        throw "Query property '$Name' must be an array"
    }
    $items = @($value)
    if (-not $AllowEmpty -and $items.Count -eq 0) {
        throw "Query property '$Name' must be a non-empty array"
    }
    for ($index = 0; $index -lt $items.Count; $index++) {
        if ($items[$index] -isnot [string] -or [string]::IsNullOrWhiteSpace($items[$index])) {
            throw "Query property '$Name' item $index must be a non-empty string"
        }
    }
    return $items
}

function Require-RunId {
    param($Object)
    if (-not (Has-Property -Object $Object -Name 'run_id')) {
        throw "Catalog query is missing property 'run_id'"
    }
    if ($Object.run_id -isnot [string] -or $Object.run_id -cne $Object.run_id.Trim() -or
        $Object.run_id -cnotmatch $script:RunIdPattern) {
        throw "Catalog query property 'run_id' must match a2_yyyyMMdd_HHmmss_<six-lowercase-hex>"
    }
    return [string]$Object.run_id
}

function Assert-RunArtifactLayout {
    param([string]$RunId, $Artifacts, [string]$ExpectedRunsDirectory)
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
    if (-not [string]::Equals(
        [System.IO.Path]::GetFullPath($runsDirectory),
        [System.IO.Path]::GetFullPath($ExpectedRunsDirectory),
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Run directory must be inside the Catalog project: $ExpectedRunsDirectory"
    }
}

function Test-PathInsideDirectory {
    param([string]$Path, [string]$Directory)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullDirectory = [System.IO.Path]::GetFullPath($Directory).TrimEnd([char[]]@('\', '/'))
    $prefix = $fullDirectory + [System.IO.Path]::DirectorySeparatorChar
    return ([string]::Equals($fullPath, $fullDirectory, [System.StringComparison]::OrdinalIgnoreCase) -or
            $fullPath.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase))
}

function Sort-Candidates {
    param([object[]]$Items)
    [object[]]$sorted = @($Items)
    if ($sorted.Count -le 1) { return $sorted }
    $comparer = [System.Collections.Generic.Comparer[object]]::Create(
        [System.Comparison[object]]{
            param($left, $right)
            $comparison = [System.Collections.Generic.Comparer[int]]::Default.Compare(
                [int]$right.relevance,
                [int]$left.relevance
            )
            if ($comparison -ne 0) { return $comparison }
            $comparison = [System.Collections.Generic.Comparer[int]]::Default.Compare(
                [int]$right.keyword_hits,
                [int]$left.keyword_hits
            )
            if ($comparison -ne 0) { return $comparison }
            $comparison = [System.Collections.Generic.Comparer[int]]::Default.Compare(
                [int]$right.agent_score,
                [int]$left.agent_score
            )
            if ($comparison -ne 0) { return $comparison }
            return [string]::Compare(
                [string]$left.id,
                [string]$right.id,
                [System.StringComparison]::Ordinal
            )
        }
    )
    [System.Array]::Sort($sorted, $comparer)
    return $sorted
}

function Test-KeywordMatch {
    param([string]$Text, [string]$Keyword)
    $pattern = '(?<![a-z0-9])' + [regex]::Escape($Keyword) + '(?![a-z0-9])'
    $options = [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
               [System.Text.RegularExpressions.RegexOptions]::CultureInvariant
    return [regex]::IsMatch($Text, $pattern, $options)
}

$resolvedRoot = [System.IO.Path]::GetFullPath($CatalogRoot)
$catalogParent = [System.IO.Path]::GetDirectoryName($resolvedRoot)
$projectRoot = if ([string]::Equals([System.IO.Path]::GetFileName($catalogParent), 'catalog', [System.StringComparison]::OrdinalIgnoreCase)) {
    [System.IO.Path]::GetDirectoryName($catalogParent)
}
else {
    $catalogParent
}
$expectedRunsDirectory = [System.IO.Path]::GetFullPath((Join-Path $projectRoot 'runs'))
$summaryPath = Join-Path $resolvedRoot 'cli-summary.json'
$dataPath = Join-Path $resolvedRoot 'data'
if (-not (Test-Path -LiteralPath $dataPath -PathType Container)) {
    throw "Catalog detail directory not found: $dataPath"
}
$summary = Read-JsonFile -Path $summaryPath -Label 'Catalog summary'
if ($summary -isnot [System.Management.Automation.PSCustomObject]) {
    throw 'Catalog summary root must be an object'
}
foreach ($propertyName in @('schema_version', 'detail_template', 'counts', 'categories')) {
    if (-not (Has-Property -Object $summary -Name $propertyName)) {
        throw "Catalog summary is missing property '$propertyName'"
    }
}
if (($summary.schema_version -isnot [int] -and $summary.schema_version -isnot [long]) -or
    [int]$summary.schema_version -ne 4) {
    throw "Unsupported Catalog summary schema_version: $($summary.schema_version)"
}
$expectedDetailTemplate = "catalog/data/{id with '/' replaced by '__'}.json"
if ([string]$summary.detail_template -cne $expectedDetailTemplate) {
    throw "Unsupported Catalog detail_template: $($summary.detail_template)"
}
if ($summary.counts -isnot [System.Management.Automation.PSCustomObject] -or
    -not (Has-Property -Object $summary.counts -Name 'total') -or
    -not (Has-Property -Object $summary.counts -Name 'categories')) {
    throw 'Catalog summary counts must contain total and categories'
}
if (($summary.counts.total -isnot [int] -and $summary.counts.total -isnot [long]) -or
    ($summary.counts.categories -isnot [int] -and $summary.counts.categories -isnot [long])) {
    throw 'Catalog summary counts must be integers'
}
$summaryCategories = @($summary.categories)
if ($summaryCategories.Count -eq 0) { throw 'Catalog summary has no categories' }
if ([int]$summary.counts.categories -ne $summaryCategories.Count) {
    throw 'Catalog summary category count does not match categories array'
}
$summaryRowCount = 0
foreach ($category in $summaryCategories) {
    foreach ($propertyName in @('name', 'count', 'rows')) {
        if (-not (Has-Property -Object $category -Name $propertyName)) {
            throw "Catalog summary category is missing property '$propertyName'"
        }
    }
    if ($category.name -isnot [string] -or [string]::IsNullOrWhiteSpace($category.name) -or
        ($category.count -isnot [int] -and $category.count -isnot [long])) {
        throw 'Catalog summary category name/count has an invalid type'
    }
    $categoryRows = @($category.rows)
    if ([int]$category.count -ne $categoryRows.Count) {
        throw "Catalog summary category '$($category.name)' count does not match its rows"
    }
    foreach ($row in $categoryRows) {
        if ($null -eq $row -or @($row).Count -ne 4) {
            throw "Malformed summary row in category '$($category.name)'"
        }
        if ($row[0] -isnot [string] -or $row[1] -isnot [string] -or $row[2] -isnot [string] -or
            ($row[3] -isnot [int] -and $row[3] -isnot [long])) {
            throw "Summary row has invalid field types in category '$($category.name)'"
        }
        if ([int]$row[3] -lt 1 -or [int]$row[3] -gt 3) {
            throw "Summary row has invalid agent score in category '$($category.name)'"
        }
    }
    $summaryRowCount += $categoryRows.Count
}
if ([int]$summary.counts.total -ne $summaryRowCount) {
    throw 'Catalog summary total does not match the category rows'
}

if ($Mode -eq 'ListCategories') {
    $categoryRows = @($summaryCategories | ForEach-Object {
        [pscustomobject][ordered]@{
            name = [string]$_.name
            count = [int]$_.count
        }
    })
    [pscustomobject][ordered]@{
        schema_version = [int]$summary.schema_version
        total = [int]$summary.counts.total
        categories = $categoryRows
    } | ConvertTo-Json -Depth 5 -Compress
    exit 0
}

foreach ($requiredPath in @(
    [pscustomobject]@{ value = $QueryPath; name = 'QueryPath' },
    [pscustomobject]@{ value = $OutputPath; name = 'OutputPath' },
    [pscustomobject]@{ value = $MetadataPath; name = 'MetadataPath' }
)) {
    if ([string]::IsNullOrWhiteSpace([string]$requiredPath.value)) {
        throw "Missing required parameter: $($requiredPath.name)"
    }
}

$fullQueryPath = [System.IO.Path]::GetFullPath($QueryPath)
$fullOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$fullMetadataPath = [System.IO.Path]::GetFullPath($MetadataPath)
foreach ($candidateOutput in @($fullOutputPath, $fullMetadataPath)) {
    if (Test-PathInsideDirectory -Path $candidateOutput -Directory $resolvedRoot) {
        throw "Output path must not be inside the read-only A1 Catalog: $candidateOutput"
    }
}
$protectedPaths = @($summaryPath, $fullQueryPath)
foreach ($candidateOutput in @($fullOutputPath, $fullMetadataPath)) {
    foreach ($protectedPath in $protectedPaths) {
        if ([string]::Equals($candidateOutput, [System.IO.Path]::GetFullPath($protectedPath), [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Output path must not overwrite an input file: $candidateOutput"
        }
    }
}
if ([string]::Equals($fullOutputPath, $fullMetadataPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'OutputPath and MetadataPath must be different files'
}

$query = Read-JsonFile -Path $fullQueryPath -Label 'Catalog query'
if ($query -isnot [System.Management.Automation.PSCustomObject]) { throw 'Catalog query root must be an object' }
$allowedQueryProperties = @('run_id', 'categories', 'keywords', 'max_candidates')
foreach ($propertyName in @($query.PSObject.Properties.Name)) {
    if ($propertyName -notin $allowedQueryProperties) {
        throw "Catalog query contains unsupported property '$propertyName'"
    }
}
$runId = Require-RunId -Object $query
Assert-RunArtifactLayout -RunId $runId -Artifacts ([ordered]@{
    'catalog-query.json' = $fullQueryPath
    'catalog-slice.json' = $fullOutputPath
    'catalog-selection.json' = $fullMetadataPath
}) -ExpectedRunsDirectory $expectedRunsDirectory
$requestedCategories = @(Require-StringArray -Object $query -Name 'categories')
$keywords = @(Require-StringArray -Object $query -Name 'keywords')
$maxCandidates = 60
if (Has-Property -Object $query -Name 'max_candidates') {
    if ($query.max_candidates -isnot [int] -and $query.max_candidates -isnot [long]) {
        throw "Catalog query property 'max_candidates' must be an integer"
    }
    $maxCandidates = [int]$query.max_candidates
}
if ($maxCandidates -lt 20 -or $maxCandidates -gt 100) {
    throw "Catalog query property 'max_candidates' must be between 20 and 100"
}
if ($requestedCategories.Count -lt 3 -or $requestedCategories.Count -gt 8) {
    throw 'Catalog query must select between 3 and 8 categories'
}
if ($keywords.Count -lt 8 -or $keywords.Count -gt 15) {
    throw 'Catalog query must contain between 8 and 15 keywords'
}

$categoryMap = New-Object System.Collections.Hashtable ([System.StringComparer]::Ordinal)
foreach ($category in $summaryCategories) {
    $name = ([string]$category.name).Trim()
    if ([string]::IsNullOrWhiteSpace($name)) { throw 'Catalog summary contains an empty category name' }
    if ($categoryMap.ContainsKey($name)) { throw "Catalog summary contains duplicate category: $name" }
    $categoryMap[$name] = $category
}

$canonicalCategories = New-Object System.Collections.Generic.List[string]
$seenCategories = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
foreach ($requestedCategory in $requestedCategories) {
    $name = $requestedCategory.Trim()
    if (-not $categoryMap.ContainsKey($name)) { throw "Unknown Catalog category: $name" }
    $canonicalName = [string]$categoryMap[$name].name
    if (-not $seenCategories.Add($canonicalName)) { throw "Duplicate Catalog category: $canonicalName" }
    $canonicalCategories.Add($canonicalName)
}

$normalizedKeywords = New-Object System.Collections.Generic.List[string]
$seenKeywords = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($keywordValue in $keywords) {
    $keyword = $keywordValue.Trim().ToLowerInvariant()
    if ($keyword.Length -gt 80) { throw "Catalog keyword is longer than 80 characters: $keyword" }
    if (-not $seenKeywords.Add($keyword)) { throw "Duplicate Catalog keyword: $keyword" }
    $normalizedKeywords.Add($keyword)
}

$selectedCategorySet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($name in $canonicalCategories) { [void]$selectedCategorySet.Add($name) }
$candidates = New-Object System.Collections.Generic.List[object]
foreach ($category in $summaryCategories) {
    $categoryName = [string]$category.name
    $categoryMatch = $selectedCategorySet.Contains($categoryName)
    foreach ($row in @($category.rows)) {
        if ($null -eq $row -or @($row).Count -lt 4) { throw "Malformed summary row in category '$categoryName'" }
        $id = ([string]$row[0]).Trim()
        $name = ([string]$row[1]).Trim()
        $function = ([string]$row[2]).Trim()
        $agentScore = [int]$row[3]
        if ([string]::IsNullOrWhiteSpace($id)) { throw "Summary category '$categoryName' contains an empty id" }
        $searchText = "$id $name $function $categoryName"
        $keywordHits = 0
        foreach ($keyword in $normalizedKeywords) {
            if (Test-KeywordMatch -Text $searchText -Keyword $keyword) { $keywordHits++ }
        }
        if (-not $categoryMatch -and $keywordHits -eq 0 -and $agentScore -lt 3) { continue }
        $relevance = ($agentScore * 10) + ($keywordHits * 25)
        if ($categoryMatch) { $relevance += 100 }
        $candidates.Add([pscustomobject][ordered]@{
            id = $id
            name = $name
            function = $function
            summary_category = $categoryName
            agent_score = $agentScore
            keyword_hits = $keywordHits
            relevance = $relevance
        })
    }
}
if ($candidates.Count -eq 0) { throw 'Catalog selection produced no candidates' }

$priority = New-Object System.Collections.Generic.List[object]
$priorityIds = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
$perCategory = [math]::Max(1, [math]::Min(5, [math]::Floor($maxCandidates / [math]::Max(1, $canonicalCategories.Count))))
foreach ($categoryName in $canonicalCategories) {
    $categoryCandidates = @(Sort-Candidates -Items @($candidates | Where-Object { $_.summary_category -ceq $categoryName }))
    foreach ($candidate in @($categoryCandidates | Select-Object -First $perCategory)) {
        if ($priorityIds.Add([string]$candidate.id)) { $priority.Add($candidate) }
    }
}
$keywordQuota = [math]::Max(5, [math]::Floor($maxCandidates * 0.30))
$keywordCandidates = @(Sort-Candidates -Items @($candidates | Where-Object { $_.keyword_hits -gt 0 }))
foreach ($candidate in @($keywordCandidates | Select-Object -First $keywordQuota)) {
    if ($priorityIds.Add([string]$candidate.id)) { $priority.Add($candidate) }
}
$agentFriendlyQuota = [math]::Max(5, [math]::Floor($maxCandidates * 0.20))
$agentFriendlyCandidates = @(Sort-Candidates -Items @($candidates | Where-Object { $_.agent_score -eq 3 }))
foreach ($candidate in @($agentFriendlyCandidates | Select-Object -First $agentFriendlyQuota)) {
    if ($priorityIds.Add([string]$candidate.id)) { $priority.Add($candidate) }
}
$globalCandidates = @(Sort-Candidates -Items $candidates.ToArray())
foreach ($candidate in $globalCandidates) {
    if ($priorityIds.Add([string]$candidate.id)) { $priority.Add($candidate) }
}

$selectedDetails = New-Object System.Collections.Generic.List[object]
$selectedIds = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]
$fallbackDescriptionCount = 0
foreach ($candidate in $priority) {
    if ($selectedDetails.Count -ge $maxCandidates) { break }
    $id = [string]$candidate.id
    if ($id.Contains('\') -or $id.Contains(':') -or @($id.Split('/')) -contains '..') {
        throw "Unsafe Catalog id: $id"
    }
    $detailFileName = $id.Replace('/', '__') + '.json'
    $detailPath = [System.IO.Path]::GetFullPath((Join-Path $dataPath $detailFileName))
    $dataPrefix = [System.IO.Path]::GetFullPath($dataPath).TrimEnd('\') + '\'
    if (-not $detailPath.StartsWith($dataPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Detail path is outside the Catalog data directory: $id"
    }
    if (-not (Test-Path -LiteralPath $detailPath -PathType Leaf)) {
        throw "Missing detail JSON: $id"
    }
    $detail = Read-JsonFile -Path $detailPath -Label "Catalog detail '$id'"
    if ($detail -isnot [System.Management.Automation.PSCustomObject]) {
        throw "Detail root is not an object: $id"
    }
    if (-not (Has-Property -Object $detail -Name 'id') -or $detail.id -isnot [string]) {
        throw "Detail id must be a string: $id"
    }
    if ($detail.id -cne $id) {
        throw "Detail id mismatch: expected '$id', got '$($detail.id)'"
    }
    if (-not (Has-Property -Object $detail -Name 'meta') -or
        $detail.meta -isnot [System.Management.Automation.PSCustomObject] -or
        -not (Has-Property -Object $detail.meta -Name 'status') -or
        $detail.meta.status -isnot [string]) {
        throw "Detail meta.status must be a string: $id"
    }
    if ($detail.meta.status -cne 'active') {
        $warnings.Add("Skipped inactive detail: $id")
        continue
    }
    if (-not (Has-Property -Object $detail -Name 'description') -or $detail.description -isnot [string]) {
        throw "Detail description must be a string: $id"
    }
    if ([string]::IsNullOrWhiteSpace($detail.description)) {
        if ([string]::IsNullOrWhiteSpace([string]$candidate.function)) {
            $warnings.Add("Skipped detail without description or summary function: $id")
            continue
        }
        $detail.description = [string]$candidate.function
        $fallbackDescriptionCount++
    }
    $selectedDetails.Add($detail)
    $selectedIds.Add($id)
}
if ($selectedDetails.Count -eq 0) { throw 'No usable Catalog details remained after validation' }

$metadata = [pscustomobject][ordered]@{
    schema_version = 1
    run_id = $runId
    source_catalog = $resolvedRoot
    source_schema_version = [int]$summary.schema_version
    source_total = [int]$summary.counts.total
    selected_categories = [string[]]$canonicalCategories.ToArray()
    keywords = [string[]]$normalizedKeywords.ToArray()
    max_candidates = $maxCandidates
    selected_count = $selectedDetails.Count
    fallback_description_count = $fallbackDescriptionCount
    candidate_ids = [string[]]$selectedIds.ToArray()
    warnings = [string[]]$warnings.ToArray()
}

Write-JsonAtomic -Value ([object[]]$selectedDetails.ToArray()) -Path $fullOutputPath
Write-JsonAtomic -Value $metadata -Path $fullMetadataPath

[pscustomobject][ordered]@{
    status = 'written'
    run_id = $runId
    output_path = $fullOutputPath
    metadata_path = $fullMetadataPath
    selected_count = $selectedDetails.Count
    fallback_description_count = $fallbackDescriptionCount
    warning_count = $warnings.Count
} | ConvertTo-Json -Compress
