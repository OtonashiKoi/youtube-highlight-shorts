import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# Approved house-caption contract. These values are a release gate, not tuning
# defaults. Change them only when the creator explicitly approves a new style.
APPROVED_CAPTION_STYLE = {
    'canvas': (1080, 610),
    'font': r'C:\Windows\Fonts\msjhbd.ttc',
    'font_size': 138,
    'minimum_font_size': 106,
    'line_width': 8,
    'max_visible_chars': 16,
    'line_spacing': 24,
    'outer_white_rim': 15,
    'inner_black_keyline': 7,
    'host_gradient_top': (255, 255, 255),
    'host_gradient_bottom': (145, 105, 205),
    'talk_caption_y': 210,
}


def assert_approved_caption_style():
    expected = {
        'canvas': (1080, 610), 'font': r'C:\Windows\Fonts\msjhbd.ttc',
        'font_size': 138, 'minimum_font_size': 106, 'line_width': 8,
        'max_visible_chars': 16, 'line_spacing': 24,
        'outer_white_rim': 15, 'inner_black_keyline': 7,
        'host_gradient_top': (255, 255, 255),
        'host_gradient_bottom': (145, 105, 205), 'talk_caption_y': 210,
    }
    if APPROVED_CAPTION_STYLE != expected:
        raise RuntimeError(
            'Approved caption style was changed. Stop release until the creator explicitly approves it.'
        )


def parse_srt(path):
    text = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    cues = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.splitlines()
        timing = next((x for x in lines if ' --> ' in x), None)
        if not timing:
            continue
        pos = lines.index(timing)
        start, end = timing.split(' --> ', 1)
        body = ''.join(lines[pos + 1:]).strip()
        if body:
            cues.append((start, end, body))
    return cues


def validate_caption_text(cues):
    assert_approved_caption_style()
    for index, (_, _, body) in enumerate(cues, 1):
        visible = len(display_body(body).replace(' ', ''))
        if visible > APPROVED_CAPTION_STYLE['max_visible_chars']:
            raise ValueError(f'Caption cue {index} exceeds 16 visible characters: {body}')


def display_body(body):
    """Strip non-printing speaker markers used by hand-reviewed SRT files."""
    return re.sub(r'^\s*\[\[(?:AI|QUOTE)\]\]\s*', '', body, flags=re.IGNORECASE)


def ass_time(value):
    h, m, rest = value.replace(',', '.').split(':')
    sec, ms = rest.split('.')
    return f'{int(h)}:{int(m):02d}:{int(sec):02d}.{round(int(ms) / 10):02d}'


def seconds(value):
    h, m, rest = value.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(rest)


def bubble_enable(srt):
    spans = [(seconds(start), seconds(end)) for start, end, body in parse_srt(srt)
             if is_bubble_body(body)]
    if not spans:
        return '0'
    return '+'.join(f'between(t,{start:.3f},{end:.3f})' for start, end in spans)


def ass_escape(text):
    return text.replace('\\', r'\\').replace('{', r'\{').replace('}', r'\}')


def wrap_cjk(text, width=9):
    if len(text) <= width:
        return text
    cut = min(range(max(1, width - 3), min(len(text), width + 3)),
              key=lambda i: 0 if text[i] in '，。！？、；： ' else 1)
    return text[:cut + 1] + r'\N' + text[cut + 1:]


def emphasize(text):
    for word in ('AI Agent', 'AI agent', 'AI', 'BUG', 'Bug', 'bug', '資料', '復原', '抱歉'):
        text = text.replace(word, r'{\c&HD88AFF&}' + word + r'{\c&HFFFFFF&}')
    return text


def is_bubble_body(body):
    if re.match(r'^\s*\[\[(?:AI|QUOTE)\]\]', body, flags=re.IGNORECASE):
        return True
    patterns = ('他跟我說', '他說', 'AI說', 'AI回', 'AI表示', '都是我的錯', '弄不出資料', '找不到')
    return any(pattern in body for pattern in patterns)


def ass_colour(rgb):
    r, g, b = rgb
    return f'&H{b:02X}{g:02X}{r:02X}&'


def gradient_text(text, start=(255, 255, 255), middle=(255, 142, 218), end=(198, 168, 255)):
    count = max(1, len(text.replace(r'\N', '')) - 1)
    result, index, pos = [], 0, 0
    while pos < len(text):
        if text[pos:pos + 2] == r'\N':
            result.append(r'\N')
            pos += 2
            continue
        t = index / count
        if t <= 0.5:
            q, left, right = t * 2, start, middle
        else:
            q, left, right = (t - 0.5) * 2, middle, end
        colour = tuple(round(left[i] + (right[i] - left[i]) * q) for i in range(3))
        result.append(r'{\c' + ass_colour(colour) + '}' + text[pos])
        index += 1
        pos += 1
    return ''.join(result) + r'{\c&HFFFFFF&}'


def tightened_times(start, end):
    start_s, end_s = seconds(start), seconds(end)
    # Keep visible text inside the recognized speech span so pauses stay clean.
    if end_s - start_s > 0.25:
        start_s += 0.03
        end_s -= 0.08
    def stamp(value):
        h, rem = divmod(max(0, value), 3600)
        m, s = divmod(rem, 60)
        return f'{int(h)}:{int(m):02d}:{s:05.2f}'
    return stamp(start_s), stamp(end_s)


def detect_silences(source):
    result = subprocess.run(
        ['ffmpeg', '-hide_banner', '-i', str(source), '-af', 'silencedetect=noise=-42dB:d=0.30',
         '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    starts = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', result.stderr)]
    ends = [float(x) for x in re.findall(r'silence_end: ([0-9.]+)', result.stderr)]
    return list(zip(starts, ends))


def visible_spans(start, end, silences):
    # Whisper boundaries can lead the audible onset slightly; bias captions late so
    # text never appears before the speaker starts.
    left, right = seconds(start) + 0.15, seconds(end) - 0.08
    spans = [(left, right)] if right > left else []
    for silence_start, silence_end in silences:
        updated = []
        for a, b in spans:
            if silence_end <= a or silence_start >= b:
                updated.append((a, b))
                continue
            if silence_start - a >= 0.12:
                updated.append((a, silence_start))
            if b - silence_end >= 0.12:
                updated.append((silence_end, b))
        spans = updated
    return spans


def ass_stamp(value):
    h, rem = divmod(max(0, value), 3600)
    m, s = divmod(rem, 60)
    return f'{int(h)}:{int(m):02d}:{s:05.2f}'


def wrap_plain(text, width=8):
    text = text.strip()
    if len(text) <= width:
        return text
    # At most two lines. Cues longer than 16 characters must be split upstream.
    cut_candidates = [i + 1 for i, char in enumerate(text[:width + 1]) if char in '，。！？、；：,.!?;: ']
    cut = cut_candidates[-1] if cut_candidates and cut_candidates[-1] >= 5 else min(width, len(text))
    return text[:cut].strip() + '\n' + text[cut:].strip()


def render_gradient_caption(text, target, quoted=False):
    assert_approved_caption_style()
    style = APPROVED_CAPTION_STYLE
    canvas = Image.new('RGBA', style['canvas'], (0, 0, 0, 0))
    lines = wrap_plain(text, style['line_width']).splitlines()[:2]
    probe = ImageDraw.Draw(canvas)
    # Keep the approved large type, but shrink just enough for eight full-width
    # glyphs plus both outlines to remain inside the 1080px frame.
    font_size = style['font_size']
    while font_size > style['minimum_font_size']:
        font = ImageFont.truetype(style['font'], font_size)
        if all(probe.textbbox((0, 0), line, font=font, stroke_width=style['outer_white_rim'])[2] <= 1020
               for line in lines):
            break
        font_size -= 2
    if quoted:
        top, bottom = (255, 255, 255), (255, 145, 174)
    else:
        top, bottom = style['host_gradient_top'], style['host_gradient_bottom']
    cursor_y = 42
    for line in lines:
        box = probe.textbbox((0, 0), line, font=font)
        width, height = box[2] - box[0], box[3] - box[1]
        x, y = (1080 - width) // 2 - box[0], cursor_y - box[1]
        # Reference stack, outside to inside: white rim, black keyline,
        # then the per-glyph gradient fill.
        probe.text((x, y), line, font=font, fill=(255, 255, 255, 255),
                   stroke_width=style['outer_white_rim'], stroke_fill=(255, 255, 255, 255))
        probe.text((x, y), line, font=font, fill=(0, 0, 0, 255),
                   stroke_width=style['inner_black_keyline'], stroke_fill=(0, 0, 0, 255))
        mask = Image.new('L', canvas.size, 0)
        ImageDraw.Draw(mask).text((x, y), line, font=font, fill=255)
        gradient = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        pixels = gradient.load()
        for row in range(cursor_y, min(canvas.height, cursor_y + height)):
            t = (row - cursor_y) / max(1, height - 1)
            colour = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
            for col in range(canvas.width):
                pixels[col, row] = colour
        canvas.alpha_composite(Image.composite(gradient, Image.new('RGBA', canvas.size), mask))
        cursor_y += height + style['line_spacing']
    canvas.save(target)


def make_caption_assets(srt, output_dir, silences):
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    for index, (start, end, body) in enumerate(parse_srt(srt), 1):
        spans = visible_spans(start, end, silences)
        if not spans:
            continue
        target = output_dir / f'{index:03d}.png'
        render_gradient_caption(display_body(body), target, quoted=is_bubble_body(body))
        assets.append((target, spans))
    return assets


def make_caption_track(assets, output_dir, duration):
    blank = output_dir / 'blank.png'
    Image.new('RGBA', APPROVED_CAPTION_STYLE['canvas'], (0, 0, 0, 0)).save(blank)
    entries, cursor = [], 0.0
    for target, spans in assets:
        for start, end in spans:
            if start > cursor:
                entries.append((blank, start - cursor))
            entries.append((target, end - start))
            cursor = end
    if cursor < duration:
        entries.append((blank, duration - cursor))
    concat = output_dir / 'captions.concat.txt'
    lines = []
    for target, span in entries:
        safe = str(target).replace('\\', '/').replace("'", "'\\''")
        lines.extend([f"file '{safe}'", f'duration {max(0.01, span):.3f}'])
    if entries:
        safe = str(entries[-1][0]).replace('\\', '/').replace("'", "'\\''")
        lines.append(f"file '{safe}'")
    concat.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    track = output_dir / 'captions.mov'
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat),
                    '-fps_mode', 'vfr', '-c:v', 'qtrle', '-pix_fmt', 'argb', str(track)], check=True)
    return track


def make_ass(srt, target, title, duration, silences):
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: PinkShadow,Microsoft JhengHei,118,&H00F58AD8,&H00FFFFFF,&H00F58AD8,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,8,20,162,266,1
Style: Subtitle,Microsoft JhengHei,118,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,11,2,8,28,170,245,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
    events = []
    for start, end, body in parse_srt(srt):
        wrapped = wrap_cjk(ass_escape(display_body(body)), 7)
        styled = emphasize(wrapped) if is_bubble_body(body) else wrapped
        for visible_start, visible_end in visible_spans(start, end, silences):
            begin, finish = ass_stamp(visible_start), ass_stamp(visible_end)
            events.append(f'Dialogue: 1,{begin},{finish},PinkShadow,,0,0,0,,{wrapped}')
            events.append(f'Dialogue: 2,{begin},{finish},Subtitle,,0,0,0,,{styled}')
    target.write_text(header + '\n'.join(events) + '\n', encoding='utf-8-sig')


def probe_duration(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                             '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
                            check=True, capture_output=True, text=True)
    value = float(result.stdout.strip())
    h, rem = divmod(value, 3600)
    m, s = divmod(rem, 60)
    return value, f'{int(h)}:{int(m):02d}:{s:05.2f}'


def derive_no_caption_output(output, explicit=None):
    if explicit:
        return Path(explicit).resolve()
    parent = output.parent
    master_parent = (parent.with_name(parent.name + '_無字幕')
                     if parent.name.lower() == 'shorts'
                     else parent / 'shorts_無字幕')
    stem = output.stem
    if stem.endswith('_直式'):
        stem += '_無字幕'
    elif not stem.endswith('_無字幕'):
        stem += '_直式_無字幕'
    return master_parent / (stem + output.suffix)


def validate_vertical_master(path, expected_duration):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries',
         'stream=codec_type,width,height,r_frame_rate,sample_aspect_ratio',
         '-show_entries', 'format=duration', '-of', 'json', str(path)],
        check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    video = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
    audio = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), None)
    actual_duration = float(data.get('format', {}).get('duration', 0))
    if not video or video.get('width') != 1080 or video.get('height') != 1920:
        raise RuntimeError(f'Invalid vertical master dimensions: {path}')
    if video.get('sample_aspect_ratio') != '1:1':
        raise RuntimeError(f'Vertical master is not square-pixel: {path}')
    if video.get('r_frame_rate') != '30/1':
        raise RuntimeError(f'Vertical master is not 30 fps: {path}')
    if not audio:
        raise RuntimeError(f'Vertical master has no audio: {path}')
    if abs(actual_duration - expected_duration) > 0.15:
        raise RuntimeError(f'Vertical master duration mismatch: {path}')


def crop_x_expression(spec, default_x):
    """Build a piecewise-linear FFmpeg crop expression from time:x keyframes."""
    if not spec:
        return str(default_x)
    points = []
    for item in spec.split(','):
        time_text, x_text = item.strip().split(':', 1)
        points.append((float(time_text), float(x_text)))
    if not points:
        return str(default_x)
    points.sort()
    if len(points) == 1:
        return f'{points[0][1]:.3f}'
    expr = f'{points[-1][1]:.3f}'
    for index in range(len(points) - 2, -1, -1):
        t0, x0 = points[index]
        t1, x1 = points[index + 1]
        if t1 <= t0:
            raise ValueError('Crop keyframe times must be strictly increasing.')
        linear = f'{x0:.3f}+(t-{t0:.3f})*{(x1 - x0) / (t1 - t0):.6f}'
        expr = f'if(lt(t,{t0:.3f}),{x0:.3f},if(lt(t,{t1:.3f}),{linear},{expr}))'
    return expr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--srt', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--no-caption-output')
    parser.add_argument('--title', required=True)
    parser.add_argument('--crop-x', type=int, default=600)
    parser.add_argument('--crop-keyframes', help='Comma-separated time:x pairs for smooth horizontal talk tracking, e.g. 0:400,3:400,10:600')
    parser.add_argument('--tracking-json', help='Per-frame VTuber head tracking generated by track-vtuber-head.py')
    parser.add_argument('--layout', choices=['talk', 'gameplay'], default='talk')
    parser.add_argument('--game-x', type=int, default=20)
    parser.add_argument('--game-y', type=int, default=174)
    parser.add_argument('--game-width', type=int, default=1380)
    parser.add_argument('--game-height', type=int, default=776)
    parser.add_argument('--host-width', type=int, default=680)
    parser.add_argument('--host-height', type=int, default=1080)
    parser.add_argument('--host-y', type=int, default=0)
    parser.add_argument('--host-scale-width', type=int, default=1320)
    parser.add_argument('--host-scale-height', type=int, default=2096)
    parser.add_argument('--host-crop-x', type=int, default=120)
    parser.add_argument('--host-crop-y', type=int, default=270)
    args = parser.parse_args()
    source, srt, output = Path(args.input).resolve(), Path(args.srt).resolve(), Path(args.output).resolve()
    no_caption_output = derive_no_caption_output(output, args.no_caption_output)
    if no_caption_output == output:
        raise ValueError('Captioned output and uncaptioned master must be different files.')
    validate_caption_text(parse_srt(srt))
    ai_logo = Path(__file__).resolve().parent.parent / 'assets' / 'ai-dialogue-logo.png'
    if not ai_logo.exists():
        raise FileNotFoundError(f'Missing AI dialogue logo: {ai_logo}')
    output.parent.mkdir(parents=True, exist_ok=True)
    no_caption_output.parent.mkdir(parents=True, exist_ok=True)
    duration_seconds, duration = probe_duration(source)
    if args.layout == 'gameplay':
        # Preserve gameplay/UI across the upper third, with the host enlarged below.
        base = (f"[0:v]crop={args.game_width}:{args.game_height}:{args.game_x}:{args.game_y},scale=1080:608[game];"
                f"[0:v]crop={args.host_width}:{args.host_height}:{args.crop_x}:{args.host_y},"
                f"scale={args.host_scale_width}:{args.host_scale_height}[host];"
                f"[host]crop=1080:1312:{args.host_crop_x}:{args.host_crop_y}[hostlower];"
                "[game][hostlower]vstack=inputs=2[bg];")
        caption_y = 590
    else:
        crop_expr = crop_x_expression(args.crop_keyframes, args.crop_x)
        base = (f"[0:v]crop=680:1080:x='{crop_expr}':y=0,scale=1580:2509[main];"
                "[main]crop=1080:1920:260:310[bg];")
        caption_y = APPROVED_CAPTION_STYLE['talk_caption_y']
    if args.tracking_json:
        if args.layout != 'talk':
            raise ValueError('--tracking-json is supported only for talk layout.')
        helper = Path(__file__).with_name('render-tracked-talk-master.py')
        subprocess.run([sys.executable, str(helper), '--input', str(source),
                        '--tracking-json', str(Path(args.tracking_json).resolve()),
                        '--output', str(no_caption_output)], check=True)
    else:
        master_vf = base + '[bg]setsar=1[master]'
        subprocess.run(['ffmpeg', '-y', '-i', source, '-filter_complex', master_vf,
                        '-map', '[master]', '-map', '0:a?',
                        '-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq', '-rc', 'vbr',
                        '-cq', '19', '-b:v', '0', '-c:a', 'aac', '-b:a', '160k', '-r', '30',
                        '-t', f'{duration_seconds:.3f}', '-movflags', '+faststart',
                        no_caption_output], check=True)
    validate_vertical_master(no_caption_output, duration_seconds)

    # The master is now fixed and verified. Only now create subtitle assets and
    # overlay them, so the captioned and uncaptioned versions share identical framing.
    silences = detect_silences(source)
    assets = make_caption_assets(srt, output.parent / (output.stem + '_字幕圖層'), silences)
    caption_track = make_caption_track(assets, output.parent / (output.stem + '_字幕圖層'), duration_seconds)
    bubble_expr = bubble_enable(srt)
    vf = ("[0:v]setsar=1[bg];" +
          "color=c=0xF06BC7:s=306x306,format=rgba,"
          "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
          "a='if(lte((X-W/2)*(X-W/2)+(Y-H/2)*(Y-H/2),(W/2)*(W/2)),255,0)'[ring];"
          "[1:v]scale=286:286,format=rgba,"
          "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
          "a='if(lte((X-W/2)*(X-W/2)+(Y-H/2)*(Y-H/2),(W/2)*(W/2)),255,0)'[bubble];"
          f"[bg][ring]overlay=387:-56:shortest=1:enable='{bubble_expr}'[ringed];"
          f"[ringed][bubble]overlay=397:-46:enable='{bubble_expr}'[layout]")
    vf += f';[layout][1:v]overlay=0:{caption_y}:shortest=1,setsar=1[caption]'
    subprocess.run(['ffmpeg', '-y', '-i', no_caption_output, '-loop', '1', '-i', ai_logo,
                    '-i', caption_track, '-filter_complex', vf.replace('[layout][1:v]', '[layout][2:v]'),
                    '-map', '[caption]', '-map', '0:a?',
                    '-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq', '-rc', 'vbr',
                    '-cq', '19', '-b:v', '0', '-c:a', 'aac', '-b:a', '160k', '-r', '30',
                    '-t', f'{duration_seconds:.3f}', '-movflags', '+faststart', output], check=True)
    print(output)


if __name__ == '__main__':
    main()
