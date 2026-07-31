param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ArtifactsDir = Join-Path $RepoRoot "artifacts"
$FrontendArtifactsDir = Join-Path $ArtifactsDir "dca-ui-dist"

if (-not (Test-Path $ArtifactsDir)) {
    New-Item -ItemType Directory -Path $ArtifactsDir | Out-Null
}

if (-not $SkipBackend) {
    Write-Host "[build] backend jar"
    Push-Location $RepoRoot
    try {
        & mvn -pl ruoyi-admin -am -DskipTests package
        if ($LASTEXITCODE -ne 0) {
            throw "Backend build failed."
        }
        Copy-Item `
            -Path (Join-Path $RepoRoot "ruoyi-admin\target\ruoyi-admin.jar") `
            -Destination (Join-Path $ArtifactsDir "ruoyi-admin.jar") `
            -Force
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipFrontend) {
    Write-Host "[build] frontend dist"
    Push-Location (Join-Path $RepoRoot "dca-ui")
    try {
        & npm ci
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend dependency install failed."
        }

        & npm run build:prod
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend build failed."
        }
    }
    finally {
        Pop-Location
    }

    if (Test-Path $FrontendArtifactsDir) {
        Remove-Item -Recurse -Force $FrontendArtifactsDir
    }
    New-Item -ItemType Directory -Path $FrontendArtifactsDir | Out-Null
    Copy-Item `
        -Path (Join-Path $RepoRoot "dca-ui\dist\*") `
        -Destination $FrontendArtifactsDir `
        -Recurse `
        -Force
}

Write-Host "[done] artifacts ready in $ArtifactsDir"