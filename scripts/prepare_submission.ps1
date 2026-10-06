[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$En2ViAdapterDir,
    [Parameter(Mandatory = $true)][string]$Vi2EnAdapterDir,
    [Parameter(Mandatory = $true)][string]$En2ViBaseModelDir,
    [Parameter(Mandatory = $true)][string]$Vi2EnBaseModelDir,
    [string]$MergedRoot = "outputs\merged",
    [string]$PackagePath = "dist\VLSP2026_MT_build_context.zip"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$mergedAbsolute = if ([IO.Path]::IsPathRooted($MergedRoot)) {
    [IO.Path]::GetFullPath($MergedRoot)
} else {
    [IO.Path]::GetFullPath((Join-Path $repoRoot $MergedRoot))
}
$repoPrefix = $repoRoot.TrimEnd("\") + "\"
if (-not ($mergedAbsolute + "\").StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "MergedRoot must stay inside the repository: $mergedAbsolute"
}

function Resolve-RequiredDirectory([string]$Path, [string]$Label) {
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
        throw "$Label is not a directory: $resolved"
    }
    return $resolved
}

$enAdapter = Resolve-RequiredDirectory $En2ViAdapterDir "EN-VI adapter"
$viAdapter = Resolve-RequiredDirectory $Vi2EnAdapterDir "VI-EN adapter"
$enBase = Resolve-RequiredDirectory $En2ViBaseModelDir "EN-VI base model"
$viBase = Resolve-RequiredDirectory $Vi2EnBaseModelDir "VI-EN base model"
$enOutput = Join-Path $mergedAbsolute "en2vi"
$viOutput = Join-Path $mergedAbsolute "vi2en"
foreach ($path in @($enOutput, $viOutput)) {
    if ((Test-Path -LiteralPath $path) -and (Get-ChildItem -LiteralPath $path -Force)) {
        throw "Merge output is not empty; use a new MergedRoot: $path"
    }
}

$previous = @{
    HF_HUB_OFFLINE = $env:HF_HUB_OFFLINE
    TRANSFORMERS_OFFLINE = $env:TRANSFORMERS_OFFLINE
    VINAI_EN2VI_MODEL_DIR = $env:VINAI_EN2VI_MODEL_DIR
    VINAI_VI2EN_MODEL_DIR = $env:VINAI_VI2EN_MODEL_DIR
}
try {
    $env:HF_HUB_OFFLINE = "1"
    $env:TRANSFORMERS_OFFLINE = "1"
    $env:VINAI_EN2VI_MODEL_DIR = $enBase
    $env:VINAI_VI2EN_MODEL_DIR = $viBase
    Push-Location $repoRoot
    try {
        & python -m src.vinai_baseline.merge_lora --config submission/configs/en2vi.json --adapter-dir $enAdapter --output-dir $enOutput
        if ($LASTEXITCODE -ne 0) { throw "EN-VI merge failed with exit code $LASTEXITCODE" }
        & python -m src.vinai_baseline.merge_lora --config submission/configs/vi2en.json --adapter-dir $viAdapter --output-dir $viOutput
        if ($LASTEXITCODE -ne 0) { throw "VI-EN merge failed with exit code $LASTEXITCODE" }
        & python scripts/validate_submission.py --en2vi-dir $enOutput --vi2en-dir $viOutput --json-output (Join-Path $mergedAbsolute "validation_report.json")
        if ($LASTEXITCODE -ne 0) { throw "Submission validation failed with exit code $LASTEXITCODE" }
        & powershell -ExecutionPolicy Bypass -File scripts/package_submission.ps1 -En2ViModelDir $enOutput -Vi2EnModelDir $viOutput -OutputPath $PackagePath
        if ($LASTEXITCODE -ne 0) { throw "Submission packaging failed with exit code $LASTEXITCODE" }
    }
    finally {
        Pop-Location
    }
}
finally {
    $env:HF_HUB_OFFLINE = $previous.HF_HUB_OFFLINE
    $env:TRANSFORMERS_OFFLINE = $previous.TRANSFORMERS_OFFLINE
    $env:VINAI_EN2VI_MODEL_DIR = $previous.VINAI_EN2VI_MODEL_DIR
    $env:VINAI_VI2EN_MODEL_DIR = $previous.VINAI_VI2EN_MODEL_DIR
}

Write-Host "Merged models: $mergedAbsolute"
Write-Host "Build context: $PackagePath"
