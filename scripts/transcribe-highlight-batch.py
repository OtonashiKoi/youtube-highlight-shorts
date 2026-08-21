import argparse
import importlib.util
from pathlib import Path

_single_path = Path(__file__).with_name('transcribe-faster-whisper.py')
_spec = importlib.util.spec_from_file_location('transcribe_faster_whisper', _single_path)
_single = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_single)
expose_windows_nvidia_dlls = _single.expose_windows_nvidia_dlls
load_model = _single.load_model
ts = _single.ts


PUNCTUATION = set('，。！？、；：,.!?;:')


def clean_word(value):
    return value.strip()


def word_units(segments):
    for seg in segments:
        for word in seg.words or []:
            text = clean_word(word.word)
            if text and word.start is not None and word.end is not None:
                yield text, word.start, word.end


def split_oversized_units(words, max_chars=16):
    """Split an oversized Whisper token and distribute its time across pieces."""
    for text, start, end in words:
        compact = text.replace(' ', '')
        if len(compact) <= max_chars:
            yield text, start, end
            continue
        pieces = [compact[i:i + max_chars] for i in range(0, len(compact), max_chars)]
        duration = max(0.01, end - start)
        total = len(compact)
        offset = 0
        for piece in pieces:
            piece_start = start + duration * offset / total
            offset += len(piece)
            piece_end = start + duration * offset / total
            yield piece, piece_start, piece_end


def chunk_words(words, max_chars=16):
    chunks, current, count = [], [], 0
    for text, start, end in words:
        visible = len(text.replace(' ', ''))
        previous_end = current[-1][2] if current else None
        gap = start - previous_end if previous_end is not None else 0
        if current and (count + visible > max_chars or gap >= 0.38):
            chunks.append(current)
            current, count = [], 0
        current.append((text, start, end))
        count += visible
        if text[-1] in PUNCTUATION or count >= max_chars:
            chunks.append(current)
            current, count = [], 0
    if current:
        chunks.append(current)
    return chunks


def join_words(chunk):
    result = ''
    for text, _, _ in chunk:
        if result and text[:1].isascii() and result[-1:].isascii() and text[0].isalnum() and result[-1].isalnum():
            result += ' '
        result += text
    return result.strip()


def transcribe_one(model, source, target, language, initial_prompt=None):
    segments, info = model.transcribe(
        str(source), language=language, beam_size=5,
        initial_prompt=initial_prompt,
        vad_filter=True, vad_parameters={'min_silence_duration_ms': 200},
        word_timestamps=True, condition_on_previous_text=False,
        hallucination_silence_threshold=1.0)
    srt_lines, txt_lines, count = [], [], 0
    # Materialize once because faster-whisper returns a lazy generator.
    chunks = chunk_words(list(split_oversized_units(word_units(segments))))
    for chunk in chunks:
        text = join_words(chunk)
        start, end = chunk[0][1], chunk[-1][2]
        count += 1
        srt_lines.extend([str(count), f'{ts(start)} --> {ts(end)}', text, ''])
        txt_lines.append(f'[{ts(start).replace(",", ".")} --> {ts(end).replace(",", ".")}] {text}')
    target.mkdir(parents=True, exist_ok=True)
    (target / f'{source.stem}.srt').write_text('\n'.join(srt_lines), encoding='utf-8-sig')
    (target / f'{source.stem}.txt').write_text('\n'.join(txt_lines) + '\n', encoding='utf-8-sig')
    return count, info.language


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clips-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--model', default='large-v3')
    parser.add_argument('--device', choices=['auto', 'cuda', 'cpu'], default='auto')
    parser.add_argument('--language', default='auto')
    parser.add_argument('--initial-prompt', default=None,
                        help='Optional terminology/context hint passed to Whisper')
    args = parser.parse_args()
    expose_windows_nvidia_dlls()
    model, backend = load_model(args.model, args.device)
    clips = sorted(Path(args.clips_dir).resolve().glob('*.mp4'))
    output = Path(args.output_dir).resolve()
    if not clips:
        raise SystemExit('No MP4 clips found')
    for index, clip in enumerate(clips, 1):
        language = None if args.language == 'auto' else args.language
        count, detected = transcribe_one(model, clip, output, language, args.initial_prompt)
        print(f'[{index}/{len(clips)}] {clip.name}: {count} cues ({detected})', flush=True)
    (output / 'transcription-method.txt').write_text(
        f'faster-whisper model={args.model} backend={backend} word_timestamps=true '
        f'initial_prompt={bool(args.initial_prompt)}\n',
        encoding='utf-8')


if __name__ == '__main__':
    main()
