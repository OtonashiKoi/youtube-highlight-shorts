import argparse
import os
import site
from pathlib import Path

from faster_whisper import WhisperModel


def expose_windows_nvidia_dlls():
    if os.name != 'nt':
        return
    candidates = []
    for base in [*site.getsitepackages(), site.getusersitepackages()]:
        root = Path(base) / 'nvidia'
        if root.is_dir():
            candidates.extend(path for path in root.glob('*/bin') if path.is_dir())
    for path in candidates:
        os.add_dll_directory(str(path))
    if candidates:
        os.environ['PATH'] = os.pathsep.join(map(str, candidates)) + os.pathsep + os.environ['PATH']


def ts(value):
    ms = max(0, round(value * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def load_model(name, device):
    if device in ('auto', 'cuda'):
        try:
            return WhisperModel(name, device='cuda', compute_type='float16'), 'cuda/float16'
        except Exception:
            if device == 'cuda':
                raise
    return WhisperModel(name, device='cpu', compute_type='int8'), 'cpu/int8'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--model', default='large-v3')
    parser.add_argument('--device', choices=['auto', 'cuda', 'cpu'], default='auto')
    parser.add_argument('--language', default='zh')
    args = parser.parse_args()
    expose_windows_nvidia_dlls()
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    model, backend = load_model(args.model, args.device)
    segments, info = model.transcribe(
        args.audio, language=args.language, beam_size=5,
        vad_filter=True, vad_parameters={'min_silence_duration_ms': 200},
        word_timestamps=True,
        condition_on_previous_text=True)
    srt_lines, txt_lines = [], []
    count = 0
    for count, seg in enumerate(segments, 1):
        text = seg.text.strip()
        if not text:
            continue
        timed_words = [word for word in (seg.words or []) if word.start is not None and word.end is not None]
        start = timed_words[0].start if timed_words else seg.start
        end = timed_words[-1].end if timed_words else seg.end
        srt_lines.extend([str(count), f'{ts(start)} --> {ts(end)}', text, ''])
        txt_lines.append(f'[{ts(start).replace(",", ".")} --> {ts(end).replace(",", ".")}] {text}')
    (root / '逐字稿.srt').write_text('\n'.join(srt_lines), encoding='utf-8-sig')
    (root / '逐字稿.txt').write_text('\n'.join(txt_lines) + '\n', encoding='utf-8-sig')
    (root / 'transcription-method.txt').write_text(
        f'faster-whisper model={args.model} backend={backend} language={info.language}\n',
        encoding='utf-8')
    print(f'Transcribed {count} segments with {backend}; detected {info.language}')


if __name__ == '__main__':
    main()
