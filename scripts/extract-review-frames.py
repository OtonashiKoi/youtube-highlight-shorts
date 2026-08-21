import argparse
import json
import math
import subprocess
from pathlib import Path


def probe_duration(video):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(video)],
        check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def seconds(value):
    parts = value.split(':')
    if len(parts) != 3:
        raise ValueError(f'Expected HH:MM:SS.mmm, got {value}')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def stamp(value):
    ms = round(value * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f'{h:02d}-{m:02d}-{s:02d}.{ms:03d}'


def extract(video, target, at, width=512):
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ['ffmpeg', '-loglevel', 'error', '-y', '-ss', f'{at:.3f}', '-i', str(video),
         '-frames:v', '1', '-vf', f'scale={width}:-2', '-c:v', 'png', '-threads', '1',
         str(target)],
        check=True)


def overview(video, out, max_frames):
    duration = probe_duration(video)
    count = max(2, min(max_frames, math.ceil(duration / 30)))
    safe_end = max(0, duration - 0.1)
    times = [safe_end * i / (count - 1) for i in range(count)]
    return [('overview', t) for t in times]


def focused(highlights, step, padding):
    data = json.loads(Path(highlights).read_text(encoding='utf-8'))
    result = []
    for item in sorted(data['highlights'], key=lambda x: int(x['index'])):
        start = max(0, seconds(item['start']) - padding)
        end = seconds(item['end']) + padding
        t = start
        while t <= end:
            result.append((f'{int(item["index"]):02d}', t))
            t += step
        if not result or result[-1][1] < end:
            result.append((f'{int(item["index"]):02d}', end))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--mode', choices=['overview', 'highlights'], default='overview')
    parser.add_argument('--highlights')
    parser.add_argument('--max-frames', type=int, default=100)
    parser.add_argument('--step', type=float, default=5.0)
    parser.add_argument('--padding', type=float, default=2.0)
    args = parser.parse_args()
    video, out = Path(args.video).resolve(), Path(args.output).resolve()
    if not video.is_file():
        raise SystemExit(f'Missing video: {video}')
    if args.mode == 'highlights' and not args.highlights:
        raise SystemExit('--highlights is required in highlights mode')
    points = (overview(video, out, args.max_frames) if args.mode == 'overview'
              else focused(args.highlights, args.step, args.padding))
    manifest = []
    for number, (group, at) in enumerate(points, 1):
        name = f'{number:04d}_{group}_t-{stamp(at)}.png'
        extract(video, out / name, at)
        manifest.append({'file': name, 'timestamp_seconds': round(at, 3), 'group': group})
    (out / f'{args.mode}-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Extracted {len(manifest)} review frames to {out}')


if __name__ == '__main__':
    main()
