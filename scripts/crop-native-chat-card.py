import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Crop an exact native chat box from a source-video frame.')
    parser.add_argument('--input', required=True)
    parser.add_argument('--at', required=True, help='Source timestamp, e.g. 00:38:12.500')
    parser.add_argument('--crop', required=True, help='FFmpeg crop w:h:x:y')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', args.at,
         '-i', str(source), '-vf', f'crop={args.crop}', '-frames:v', '1', str(output)],
        check=True,
    )
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError('Chat-card crop was not created.')
    print(output)


if __name__ == '__main__':
    main()
