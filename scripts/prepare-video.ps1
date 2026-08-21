#requires -Version 7.0
param(
    [Parameter(Mandatory)][ValidatePattern('^https?://')][string]$Url,
    [Parameter(Mandatory)][string]$OutputDir
)
$ErrorActionPreference = 'Stop'
$resolved = [System.IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $resolved | Out-Null

$format = 'bv*[height>=1080]+ba/b[height>=1080]'
yt-dlp --no-playlist --write-info-json --write-subs --write-auto-subs `
    --sub-langs 'zh-TW,zh-Hant,zh-Hans,zh,en' --convert-subs srt `
    -f $format --merge-output-format mp4 `
    -o (Join-Path $resolved 'source.%(ext)s') $Url

$video = Get-ChildItem -LiteralPath $resolved -File | Where-Object {
    $_.Name -match '^source\.(mp4|mkv|webm)$'
} | Select-Object -First 1
if (-not $video) { throw 'Downloaded source video was not found.' }
if ($video.Extension -ne '.mp4') {
    ffmpeg -y -i $video.FullName -map 0 -c copy (Join-Path $resolved 'source.mp4')
} elseif ($video.Name -ne 'source.mp4') {
    Move-Item -LiteralPath $video.FullName -Destination (Join-Path $resolved 'source.mp4')
}
ffmpeg -y -i (Join-Path $resolved 'source.mp4') -vn -ac 1 -ar 16000 -c:a pcm_s16le `
    (Join-Path $resolved 'source-audio.wav')

$probe = ffprobe -v error -select_streams v:0 -show_entries stream=width,height `
    -of json (Join-Path $resolved 'source.mp4') | ConvertFrom-Json
$stream = $probe.streams | Select-Object -First 1
if (-not $stream -or $stream.width -lt 1920 -or $stream.height -lt 1080) {
    throw "Release gate failed: source is $($stream.width)x$($stream.height), not genuine 1080p or higher."
}

$info = Get-ChildItem -LiteralPath $resolved -File -Filter 'source*.info.json' | Select-Object -First 1
if ($info -and $info.Name -ne 'source.info.json') {
    Move-Item -LiteralPath $info.FullName -Destination (Join-Path $resolved 'source.info.json')
}
Write-Output $resolved
