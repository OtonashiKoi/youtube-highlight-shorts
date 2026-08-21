#requires -Version 7.0
$ErrorActionPreference = 'Stop'
$required = @('yt-dlp', 'ffmpeg', 'ffprobe', 'python')
$missing = foreach ($name in $required) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { $name }
}
if ($missing) {
    throw "Missing required commands: $($missing -join ', ')"
}
$required | ForEach-Object {
    $cmd = Get-Command $_
    [pscustomobject]@{ Command = $_; Path = $cmd.Source }
} | Format-Table -AutoSize

$pythonModules = @('PIL', 'cv2', 'numpy', 'faster_whisper')
$missingModules = foreach ($module in $pythonModules) {
    python -c "import $module" 2>$null
    if ($LASTEXITCODE -ne 0) { $module }
}
if ($missingModules) {
    throw "Missing Python modules: $($missingModules -join ', '). See references/setup.md."
}
