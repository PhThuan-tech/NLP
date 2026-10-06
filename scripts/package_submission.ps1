[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$En2ViModelDir,

    [Parameter(Mandatory = $true)]
    [string]$Vi2EnModelDir,

    [string]$OutputPath = "VLSP2026_MT_build_context.zip"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Resolve-And-TestModel {
    param(
        [string]$Path,
        [string]$Direction,
        [string]$ExpectedBaseModel,
        [string]$ExpectedRevision
    )

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
        throw "$Direction model path is not a directory: $resolved"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $resolved "config.json") -PathType Leaf)) {
        throw "$Direction merged model is missing config.json: $resolved"
    }
    $weights = @(
        Get-ChildItem -LiteralPath $resolved -File |
            Where-Object { $_.Name -match '^(model.*\.safetensors|pytorch_model.*\.bin)$' }
    )
    if ($weights.Count -eq 0) {
        throw "$Direction merged model has no model weights: $resolved"
    }
    $tokenizerFiles = @(
        Get-ChildItem -LiteralPath $resolved -File |
            Where-Object { $_.Name -match '^(tokenizer.*|sentencepiece.*|spiece.*|source\.spm|target\.spm)' }
    )
    if ($tokenizerFiles.Count -eq 0) {
        throw "$Direction merged model has no tokenizer files: $resolved"
    }
    $manifestPath = Join-Path $resolved "merge_manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "$Direction model is missing merge_manifest.json. Merge it with src.vinai_baseline.merge_lora before packaging."
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.direction -ne $Direction) {
        throw "$Direction manifest reports direction '$($manifest.direction)'"
    }
    if ($manifest.base_model -ne $ExpectedBaseModel) {
        throw "$Direction manifest reports the wrong base model: $($manifest.base_model)"
    }
    if ($manifest.base_model_revision -ne $ExpectedRevision) {
        throw "$Direction manifest reports the wrong base revision: $($manifest.base_model_revision)"
    }
    return $resolved
}

$en2vi = Resolve-And-TestModel `
    -Path $En2ViModelDir `
    -Direction "en2vi" `
    -ExpectedBaseModel "vinai/vinai-translate-en2vi-v2" `
    -ExpectedRevision "1e47495b5dac16097b1d9e7b4133c27e1f40504f"
$vi2en = Resolve-And-TestModel `
    -Path $Vi2EnModelDir `
    -Direction "vi2en" `
    -ExpectedBaseModel "vinai/vinai-translate-vi2en-v2" `
    -ExpectedRevision "4eb2219d447d4352861e71e371a6b6abcb0509c8"

& python (Join-Path $repoRoot "scripts\validate_submission.py") `
    --en2vi-dir $en2vi `
    --vi2en-dir $vi2en
if ($LASTEXITCODE -ne 0) {
    throw "Merged-model validation failed with exit code $LASTEXITCODE"
}

$outputAbsolute = if ([IO.Path]::IsPathRooted($OutputPath)) {
    [IO.Path]::GetFullPath($OutputPath)
}
else {
    [IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath))
}
if ([IO.Path]::GetExtension($outputAbsolute) -ne ".zip") {
    throw "OutputPath must end in .zip: $outputAbsolute"
}
$outputParent = [IO.Path]::GetDirectoryName($outputAbsolute)
if (-not (Test-Path -LiteralPath $outputParent -PathType Container)) {
    New-Item -ItemType Directory -Path $outputParent -Force | Out-Null
}

$stage = Join-Path ([IO.Path]::GetTempPath()) ("vlsp_submission_" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $stage | Out-Null

try {
    Copy-Item -LiteralPath (Join-Path $repoRoot "src") -Destination (Join-Path $stage "src") -Recurse
    Copy-Item -LiteralPath (Join-Path $repoRoot "submission") -Destination (Join-Path $stage "submission") -Recurse

    $stagedModels = Join-Path $stage "submission\models"
    New-Item -ItemType Directory -Path (Join-Path $stagedModels "en2vi") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $stagedModels "vi2en") -Force | Out-Null
    Copy-Item -Path (Join-Path $en2vi "*") -Destination (Join-Path $stagedModels "en2vi") -Recurse -Force
    Copy-Item -Path (Join-Path $vi2en "*") -Destination (Join-Path $stagedModels "vi2en") -Recurse -Force

    # Never ship local bytecode/cache files in the Linux build context.
    Get-ChildItem -LiteralPath $stage -Directory -Recurse -Force |
        Where-Object Name -eq "__pycache__" |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $stage -File -Recurse -Force |
        Where-Object Extension -in ".pyc", ".pyo" |
        Remove-Item -Force

    if (Test-Path -LiteralPath $outputAbsolute) {
        Remove-Item -LiteralPath $outputAbsolute -Force
    }
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::Open($outputAbsolute, [IO.Compression.ZipArchiveMode]::Create)
    try {
        Get-ChildItem -LiteralPath $stage -File -Recurse | Sort-Object FullName | ForEach-Object {
            $relative = $_.FullName.Substring($stage.Length).TrimStart('\', '/') -replace '\\', '/'
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive,
                $_.FullName,
                $relative,
                [IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    }
    finally {
        $archive.Dispose()
    }

    $md5 = (Get-FileHash -LiteralPath $outputAbsolute -Algorithm MD5).Hash.ToLowerInvariant()
    $md5Path = "$outputAbsolute.md5"
    [IO.File]::WriteAllText($md5Path, "$md5  $([IO.Path]::GetFileName($outputAbsolute))`n", [Text.UTF8Encoding]::new($false))

    Write-Host "Created: $outputAbsolute"
    Write-Host "MD5:     $md5"
    Write-Host "Checksum: $md5Path"
    Write-Host "Next: extract the ZIP, then docker build -f submission/Dockerfile -t vlsp2026-legal-mt:latest ."
}
finally {
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
