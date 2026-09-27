[CmdletBinding()]
param(
    [string]$OutputPath = "NLP_colab.zip"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$output = [IO.Path]::GetFullPath((Join-Path $projectRoot $OutputPath))
$stage = Join-Path ([IO.Path]::GetTempPath()) ("nlp_colab_" + [guid]::NewGuid())

$required = @(
    "README",
    "requirements.txt",
    "requirements-training.txt",
    "requirements-training-colab.txt",
    "configs",
    "src",
    "tests",
    "docs",
    "notebooks\02_vinai_colab.ipynb",
    "artifacts\processed_clean_seed67_v2"
)

try {
    New-Item -ItemType Directory -Path $stage | Out-Null
    foreach ($relative in $required) {
        $source = Join-Path $projectRoot $relative
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Missing required Colab content: $source"
        }
        $destination = Join-Path $stage $relative
        $destinationParent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
    }

    # Tests/imports may have recreated bytecode since the last cleanup. Never
    # ship machine-specific caches even when they exist in the source tree.
    Get-ChildItem -LiteralPath $stage -Directory -Recurse -Force |
        Where-Object Name -eq "__pycache__" |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $stage -File -Recurse -Force |
        Where-Object Extension -in ".pyc", ".pyo" |
        Remove-Item -Force

    if (Test-Path -LiteralPath $output) {
        Remove-Item -LiteralPath $output -Force
    }
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $output -CompressionLevel Optimal
    $sizeMb = [math]::Round((Get-Item -LiteralPath $output).Length / 1MB, 2)
    Write-Host "Created: $output ($sizeMb MB)"
}
finally {
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
