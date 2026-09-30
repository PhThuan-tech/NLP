[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("prepare", "audit", "freeze")]
    [string]$Stage,
    [Nullable[double]]$SemanticThreshold,
    [string]$SemanticModel = "sentence-transformers/LaBSE",
    [string]$SemanticModelRevision = "836121a",
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$parentDir = Join-Path $projectRoot "artifacts/processed_token448_seed67_v3_parent"
$auditDir = Join-Path $projectRoot "artifacts/processed_semantic_audit_seed67_v3"
$frozenDir = Join-Path $projectRoot "artifacts/processed_clean_semantic_seed67_v3"
$overwriteArgs = if ($Overwrite) { @("--overwrite") } else { @() }

Push-Location $projectRoot
try {
    if ($Stage -eq "prepare") {
        python -m src.data.prepare `
            --project-root . `
            --output-dir $parentDir `
            --seed 67 `
            --dataset-version token448_seed67_v3_parent `
            --minimum-alignment-score 0.75 `
            --maximum-block-words 220 `
            --maximum-chunk-words 220 `
            --maximum-chunk-tokens 448 `
            --tokenizer-model vinai/vinai-translate-en2vi-v2 `
            --tokenizer-revision 1e47495b5dac16097b1d9e7b4133c27e1f40504f `
            @overwriteArgs
        if ($LASTEXITCODE -ne 0) { throw "Token-aware preparation failed" }
    }
    elseif ($Stage -eq "audit") {
        python -m src.data.finalize `
            --input-dir $parentDir `
            --output-dir $auditDir `
            --dataset-id legal_envi_semantic_audit_seed67_v3 `
            --split-seed 67 `
            --minimum-alignment-score 0.75 `
            --semantic-model $SemanticModel `
            --semantic-model-revision $SemanticModelRevision `
            @overwriteArgs
        if ($LASTEXITCODE -ne 0) { throw "Semantic audit failed" }
        Write-Host "Review: $auditDir/semantic_audit.json"
    }
    else {
        if ($null -eq $SemanticThreshold) {
            throw "-SemanticThreshold is required for the freeze stage"
        }
        python -m src.data.finalize `
            --input-dir $auditDir `
            --output-dir $frozenDir `
            --dataset-id legal_envi_clean_semantic_seed67_v3 `
            --split-seed 67 `
            --minimum-alignment-score 0.75 `
            --semantic-model $SemanticModel `
            --semantic-model-revision $SemanticModelRevision `
            --minimum-semantic-similarity $SemanticThreshold `
            --reuse-semantic-scores `
            @overwriteArgs
        if ($LASTEXITCODE -ne 0) { throw "Semantic freeze failed" }
        Write-Host "Frozen v3: $frozenDir"
    }
}
finally {
    Pop-Location
}
