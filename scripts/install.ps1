$ErrorActionPreference = 'Stop'

$SourceDir = Split-Path -Parent $PSScriptRoot
if ($env:AGENT_SKILLS_HOME) {
    $DestRoot = $env:AGENT_SKILLS_HOME
} elseif ($env:CODEX_HOME) {
    $DestRoot = Join-Path $env:CODEX_HOME 'skills'
} else {
    $DestRoot = Join-Path $HOME '.codex\skills'
}
$Dest = Join-Path $DestRoot 'sd-pixelprocessor-agent'

New-Item -ItemType Directory -Force -Path $DestRoot | Out-Null
$SourceResolved = (Resolve-Path -LiteralPath $SourceDir).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
$DestRootResolved = (Resolve-Path -LiteralPath $DestRoot).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
$DestResolved = [IO.Path]::GetFullPath($Dest).TrimEnd([IO.Path]::DirectorySeparatorChar)
if ($SourceResolved -eq $DestResolved) {
    Write-Host "Already installed at: $DestResolved"
    exit 0
}
if (-not $DestResolved.StartsWith($DestRootResolved + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing install target outside destination root: $DestResolved"
}
$Python = if ($env:SD_PIXEL_AGENT_PYTHON) { $env:SD_PIXEL_AGENT_PYTHON } else { 'python' }
& $Python -B (Join-Path $PSScriptRoot 'install_transaction.py') --source $SourceDir --destination $DestResolved
if ($LASTEXITCODE -ne 0) { throw 'Transactional install failed; inspect stage/backup and install-lock.' }
