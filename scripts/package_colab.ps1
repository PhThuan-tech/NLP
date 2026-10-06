[CmdletBinding()]
param(
    [string]$OutputPath = "NLP_colab.zip",
    [string]$DatasetPath = "artifacts\processed_clean_semantic_seed67_v3",
    [string]$ResultZipPath = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$output = [IO.Path]::GetFullPath((Join-Path $projectRoot $OutputPath))
$stage = Join-Path ([IO.Path]::GetTempPath()) ("nlp_colab_" + [guid]::NewGuid())
$datasetAbsolute = (Resolve-Path -LiteralPath (Join-Path $projectRoot $DatasetPath)).Path
$projectPrefix = $projectRoot.TrimEnd("\") + "\"
if (-not $datasetAbsolute.StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "DatasetPath must stay inside the project: $datasetAbsolute"
}
$datasetRelative = $datasetAbsolute.Substring($projectPrefix.Length)

$required = @(
    "README.md",
    "requirements.txt",
    "requirements-training.txt",
    "requirements-training-colab.txt",
    "requirements-semantic.txt",
    "configs",
    "src",
    "tests",
    "docs",
    "scripts",
    "submission",
    "data\instruction.md",
    "notebooks\03_vinai_kaggle.ipynb",
    "notebooks\04_v3_builder_kaggle.ipynb",
    "notebooks\05_inference_pipeline_kaggle.ipynb",
    $datasetRelative
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

    if ($ResultZipPath) {
        $resultZip = (Resolve-Path -LiteralPath (Join-Path $projectRoot $ResultZipPath)).Path
        if (-not (Test-Path -LiteralPath $resultZip -PathType Leaf)) {
            throw "ResultZipPath is not a file: $resultZip"
        }
        if ([IO.Path]::GetExtension($resultZip) -ne ".zip") {
            throw "ResultZipPath must be a ZIP file: $resultZip"
        }
        $attachedRuns = Join-Path $stage "attached_runs"
        New-Item -ItemType Directory -Path $attachedRuns -Force | Out-Null
        Copy-Item -LiteralPath $resultZip -Destination (Join-Path $attachedRuns ([IO.Path]::GetFileName($resultZip))) -Force
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
    # Compress-Archive stores Windows path separators (\) in entry names.
    # Kaggle rejects those entries, so build the archive explicitly with the
    # ZIP-standard POSIX separator (/). Colab accepts the same archive.
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zipStream = [IO.File]::Open(
        $output,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::ReadWrite,
        [IO.FileShare]::None
    )
    try {
        $archive = [IO.Compression.ZipArchive]::new(
            $zipStream,
            [IO.Compression.ZipArchiveMode]::Create,
            $false,
            [Text.Encoding]::UTF8
        )
        try {
            Get-ChildItem -LiteralPath $stage -File -Recurse -Force | ForEach-Object {
                # Windows PowerShell 5.1 uses a .NET version without
                # Path.GetRelativePath. Every enumerated file is a verified
                # descendant of $stage, so a prefix slice is deterministic.
                $relative = $_.FullName.Substring($stage.Length + 1)
                $entryName = $relative.Replace("\", "/")
                [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                    $archive,
                    $_.FullName,
                    $entryName,
                    [IO.Compression.CompressionLevel]::Optimal
                ) | Out-Null
            }
        }
        finally {
            $archive.Dispose()
        }
    }
    finally {
        $zipStream.Dispose()
    }
    $sizeMb = [math]::Round((Get-Item -LiteralPath $output).Length / 1MB, 2)
    Write-Host "Created: $output ($sizeMb MB)"
}
finally {
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
