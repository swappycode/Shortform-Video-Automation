# ffmpeg_fetch.ps1
param(
  [string]$dest = "bundled_tools/ffmpeg/bin",
  [string]$provider = "gyan"  # "gyan" or "btbn"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

if ($provider -eq "gyan") {
  $url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
} else {
  # BtbN: choose lgpl or gpl - here we use essentials/generic release artifacts from GitHub Releases
  # BtbN exposes zips per build; using 'latest' redirect page is possible but we use recommended Gyan by default.
  Write-Host "Using BtbN is not implemented by default; set provider to 'gyan' or modify script."
  exit 1
}

$zip = "ffmpeg_temp.zip"
Write-Host "Downloading $url ..."
Invoke-WebRequest -Uri $url -OutFile $zip

Write-Host "Extracting ..."
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path $zip), "ffmpeg_temp")

# find ffmpeg.exe inside extracted tree
$ff = Get-ChildItem -Path "ffmpeg_temp" -Filter "ffmpeg.exe" -Recurse -File | Select-Object -First 1
$fp = Get-ChildItem -Path "ffmpeg_temp" -Filter "ffprobe.exe" -Recurse -File | Select-Object -First 1

if ($ff -eq $null -or $fp -eq $null) {
  Write-Host "Failed to find ffmpeg.exe or ffprobe.exe in archive"
  Remove-Item -Recurse -Force "ffmpeg_temp"
  Remove-Item -Force $zip
  exit 1
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path $ff.FullName -Destination (Join-Path $dest "ffmpeg.exe") -Force
Copy-Item -Path $fp.FullName -Destination (Join-Path $dest "ffprobe.exe") -Force

Write-Host "ffmpeg + ffprobe copied to $dest"

Remove-Item -Recurse -Force "ffmpeg_temp"
Remove-Item -Force $zip
