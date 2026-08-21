import argparse
import json
import re
import subprocess
from pathlib import Path


def probe(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries',
         'stream=codec_type,codec_name,width,height,r_frame_rate,sample_aspect_ratio:format=duration',
         '-of', 'json', str(path)], check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def validate_srt(path):
    text = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    cues = 0
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.splitlines()
        timing = next((line for line in lines if ' --> ' in line), None)
        if not timing:
            continue
        body = ''.join(lines[lines.index(timing) + 1:]).strip()
        visible = len(re.sub(r'^\s*\[\[(?:AI|QUOTE)\]\]\s*', '', body).replace(' ', ''))
        if visible > 16:
            raise ValueError(f'{path.name}: cue exceeds 16 visible characters: {body}')
        cues += 1
    if not cues:
        raise ValueError(f'{path.name}: no subtitle cues found')
    return cues


def main():
    parser = argparse.ArgumentParser(description='Enforce the final YouTube Shorts release gates.')
    parser.add_argument('--source', required=True)
    parser.add_argument('--short', action='append', default=[])
    parser.add_argument('--srt', action='append', default=[])
    parser.add_argument('--proofread-marker', required=True,
                        help='JSON containing llm_proofread=true and traditional_chinese_audited=true')
    args = parser.parse_args()

    source_info = probe(Path(args.source).resolve())
    source_video = next((s for s in source_info['streams'] if s['codec_type'] == 'video'), None)
    if not source_video or source_video.get('width', 0) < 1920 or source_video.get('height', 0) < 1080:
        raise RuntimeError('Source-quality gate failed: genuine 1080p or higher is required.')

    marker = json.loads(Path(args.proofread_marker).read_text(encoding='utf-8-sig'))
    if marker.get('llm_proofread') is not True or marker.get('traditional_chinese_audited') is not True:
        raise RuntimeError('Subtitle-proofreading gate failed.')

    cue_count = sum(validate_srt(Path(path).resolve()) for path in args.srt)
    for item in args.short:
        info = probe(Path(item).resolve())
        video = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
        audio = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
        if not video or (video.get('width'), video.get('height')) != (1080, 1920):
            raise RuntimeError(f'Output geometry gate failed: {item}')
        if video.get('r_frame_rate') != '30/1' or video.get('sample_aspect_ratio') not in ('1:1', None):
            raise RuntimeError(f'Output frame-rate/SAR gate failed: {item}')
        if not audio:
            raise RuntimeError(f'Output audio gate failed: {item}')
    print(json.dumps({'status': 'pass', 'shorts': len(args.short), 'subtitle_cues': cue_count}, ensure_ascii=False))


if __name__ == '__main__':
    main()
