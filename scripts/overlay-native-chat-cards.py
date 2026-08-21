import argparse
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Overlay verified native chat-card bitmaps on a 9:16 Short.')
    parser.add_argument('--input', required=True)
    parser.add_argument('--cards', required=True, help='UTF-8 JSON array; see references/chat-cards.md')
    parser.add_argument('--output', required=True)
    parser.add_argument('--width', type=int, default=900)
    parser.add_argument('--y', type=int, default=1450)
    parser.add_argument('--encoder', choices=['h264_nvenc', 'libx264'], default='h264_nvenc')
    args = parser.parse_args()

    source = Path(args.input).resolve()
    spec_path = Path(args.cards).resolve()
    output = Path(args.output).resolve()
    cards = json.loads(spec_path.read_text(encoding='utf-8-sig'))
    if not isinstance(cards, list):
        raise ValueError('Cards JSON must be an array.')

    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source)]
    filters = ['[0:v]setsar=1[v0]']
    current = 'v0'
    for index, card in enumerate(cards, 1):
        asset = (spec_path.parent / card['asset']).resolve()
        start, end = float(card['start']), float(card['end'])
        if not asset.exists() or end <= start:
            raise ValueError(f'Invalid chat card {index}: {card}')
        command.extend(['-loop', '1', '-i', str(asset)])
        filters.append(f'[{index}:v]scale={args.width}:-1[c{index}]')
        next_name = f'v{index}'
        filters.append(
            f"[{current}][c{index}]overlay=(W-w)/2:{args.y}:"
            f"enable='between(t,{start:.3f},{end:.3f})':eof_action=pass[{next_name}]"
        )
        current = next_name

    output.parent.mkdir(parents=True, exist_ok=True)
    video_args = (
        ['-c:v', 'h264_nvenc', '-preset', 'p6', '-tune', 'hq', '-rc', 'vbr', '-cq', '18', '-b:v', '0']
        if args.encoder == 'h264_nvenc'
        else ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18']
    )
    command.extend([
        '-filter_complex', ';'.join(filters), '-map', f'[{current}]', '-map', '0:a?',
        *video_args, '-c:a', 'copy', '-r', '30', '-movflags', '+faststart', '-shortest', str(output),
    ])
    subprocess.run(command, check=True)
    print(output)


if __name__ == '__main__':
    main()
