import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clips-dir', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    clips = sorted(Path(args.clips_dir).resolve().glob('*.mp4'))
    if not clips:
        raise SystemExit('No clips found')
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = output.with_suffix('.concat.txt')
    lines = ["file '" + str(p).replace('\\', '/').replace("'", "'\\''") + "'" for p in clips]
    manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(manifest),
                    '-c', 'copy', '-movflags', '+faststart', str(output)], check=True)
    manifest.unlink()
    print(f'Created {output} from {len(clips)} clips')


if __name__ == '__main__':
    main()
