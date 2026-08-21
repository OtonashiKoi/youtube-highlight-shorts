import argparse
import json
import re
import subprocess
from pathlib import Path


def run(args):
    subprocess.run([str(x) for x in args], check=True)


def has_encoder(name):
    result = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True)
    return name in result.stdout


def media_ok(path):
    if not path.is_file() or path.stat().st_size == 0:
        return False
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
        capture_output=True, text=True)
    try:
        return result.returncode == 0 and float(result.stdout.strip()) > 0
    except ValueError:
        return False


def video_args(encoder, quality):
    if encoder == 'h264_nvenc':
        return ['-c:v', encoder, '-preset', 'p5', '-tune', 'hq', '-rc', 'vbr',
                '-cq', str(quality), '-b:v', '0']
    return ['-c:v', 'libx264', '-preset', 'medium', '-crf', str(quality)]


def safe_name(text):
    text = re.sub(r'[<>:"/\\|?*]', '', text).strip().rstrip('.')
    return text[:80] or 'highlight'


def parse_time(value):
    parts = value.replace(',', '.').split(':')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def srt_time(value):
    ms = max(0, round(value * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def read_srt(path):
    text = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    cues = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.splitlines()
        timing = next((line for line in lines if ' --> ' in line), None)
        if not timing:
            continue
        pos = lines.index(timing)
        start, end = timing.split(' --> ', 1)
        body = '\n'.join(lines[pos + 1:]).strip()
        if body:
            cues.append((parse_time(start), parse_time(end), body))
    return cues


def write_segment_srt(cues, start, end, target):
    lines, number = [], 1
    for cue_start, cue_end, body in cues:
        if cue_end <= start or cue_start >= end:
            continue
        local_start = max(cue_start, start) - start
        local_end = min(cue_end, end) - start
        lines.extend([str(number), f'{srt_time(local_start)} --> {srt_time(local_end)}', body, ''])
        number += 1
    target.write_text('\n'.join(lines), encoding='utf-8-sig')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', required=True)
    parser.add_argument('--highlights', required=True)
    parser.add_argument('--encoder', choices=['auto', 'libx264', 'h264_nvenc'], default='auto')
    args = parser.parse_args()
    root = Path(args.input_dir).resolve()
    encoder = ('h264_nvenc' if args.encoder == 'auto' and has_encoder('h264_nvenc')
               else ('libx264' if args.encoder == 'auto' else args.encoder))
    source = root / 'source.mp4'
    if not source.is_file():
        raise SystemExit(f'Missing {source}')
    data = json.loads(Path(args.highlights).read_text(encoding='utf-8'))
    items = sorted(data['highlights'], key=lambda x: int(x['index']))
    clips, shorts, subs = root / 'clips', root / 'shorts', root / '字幕SRT'
    for folder in (clips, shorts, subs):
        folder.mkdir(parents=True, exist_ok=True)
    transcript = root / '逐字稿.srt'
    cues = read_srt(transcript) if transcript.is_file() else []
    concat_lines = []
    for item in items:
        idx = int(item['index'])
        stem = f'{idx:02d}_{safe_name(item["title"])}'
        clip = clips / f'{stem}.mp4'
        short = shorts / f'{stem}_直式.mp4'
        if cues:
            write_segment_srt(cues, parse_time(item['start']), parse_time(item['end']),
                              subs / f'{stem}.srt')
        if not media_ok(clip):
            run(['ffmpeg', '-y', '-ss', item['start'], '-to', item['end'], '-i', source,
                 '-map', '0:v:0', '-map', '0:a?', *video_args(encoder, 18),
                 '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', clip])
        vf = ('[0:v]scale=270:480:force_original_aspect_ratio=increase,'
              'crop=270:480,boxblur=12:6,scale=1080:1920[bg];'
              '[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];'
              '[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1')
        if not media_ok(short):
            run(['ffmpeg', '-y', '-i', clip, '-filter_complex', vf, '-map', '0:a?',
                 *video_args(encoder, 20), '-c:a', 'aac',
                 '-b:a', '160k', '-r', '30', '-movflags', '+faststart', short])
        concat_lines.append("file '" + str(clip).replace("'", "'\\''") + "'")
    concat_file = root / 'concat.txt'
    concat_file.write_text('\n'.join(concat_lines) + '\n', encoding='utf-8')
    run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
         '-c', 'copy', '-movflags', '+faststart', root / '精華合輯.mp4'])
    print(f'Rendered {len(items)} highlights in {root} with {encoder}')


if __name__ == '__main__':
    main()
