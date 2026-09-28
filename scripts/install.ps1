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
if (Test-Path $Dest) {
    $Stamp = Get-Date -Format 'yyyyMMddHHmmss'
    $Backup = "$Dest.backup.$Stamp"
    Copy-Item -Recurse -Force $Dest $Backup
    Write-Host "Existing skill backed up to: $Backup"
    Remove-Item -Recurse -Force $Dest
}
Copy-Item -Recurse -Force $SourceDir $Dest
Write-Host "Installed: $Dest"
Write-Host 'Invoke with: $sd-pixelprocessor-agent'
