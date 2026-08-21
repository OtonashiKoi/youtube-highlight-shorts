# Setup and tools

## Supported baseline

- Windows 10/11 with PowerShell 7 or newer.
- Python 3.10 or newer.
- FFmpeg and FFprobe 6 or newer.
- `yt-dlp` for authorized YouTube downloads.
- NVIDIA GPU plus an FFmpeg build with NVENC for the default fast renderer. CPU rendering remains available in scripts that expose `--encoder libx264`.
- Microsoft JhengHei Bold at `C:\Windows\Fonts\msjhbd.ttc` for the locked house-caption style.
- Codex/ChatGPT built-in image generation is optional and is used only when the creator explicitly authorizes reconstruction of an unreadable source chat card. It does not require an API key. Always retain the corresponding source/replay evidence.

## Install

```powershell
winget install --id Microsoft.PowerShell --source winget
winget install --id Gyan.FFmpeg --source winget
python -m pip install --upgrade yt-dlp
python -m pip install -r requirements.txt
pwsh -File scripts/check-dependencies.ps1
```

For NVIDIA Faster Whisper on Windows, install the CUDA/cuDNN runtime versions required by the installed `ctranslate2` release. The transcription scripts automatically expose NVIDIA wheel DLL directories when present and fall back to CPU when `--device auto` cannot initialize CUDA.

## Core commands

```powershell
pwsh -File scripts/prepare-video.ps1 -Url <authorized-url> -OutputDir <project>
python scripts/transcribe-faster-whisper.py --audio <project>/source-audio.wav --output-dir <project> --model large-v3 --language auto
python scripts/extract-review-frames.py --video <project>/source.mp4 --output <project>/review-frames --mode overview
python scripts/render-highlights.py --input-dir <project> --highlights <project>/highlights.json
```

Read `talk-short-style.md` before running the talk renderer. The renderer fails when the locked caption contract is altered.
