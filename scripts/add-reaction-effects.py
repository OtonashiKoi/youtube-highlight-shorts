import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


EVENTS = [
    (17.9, 21.2, 'AI 執行中…', '🤖', '#8E74E8', 610, 1580, -4),
    (28.9, 36.2, '資料回滾！？', '⏪', '#FF4F82', 48, 1580, 3),
    (40.4, 44.3, 'AI：都是我的錯', '🙇', '#FF91AE', 610, 1580, -3),
    (49.8, 54.3, '然後呢？', '？？', '#FFD45E', 48, 1580, 4),
    (59.2, 64.0, '找不到資料', '404', '#FF5B62', 610, 1580, -3),
    (82.2, 87.9, '幸好有備份！', '💾', '#70D7C7', 48, 1580, 3),
    (104.8, 113.9, '擺爛模式 ON', '🫠', '#FF9E57', 610, 1580, -3),
    (116.0, 120.2, '超 級 無 語', '💢', '#A98CF2', 48, 1580, 3),
]


def font(path, size):
    return ImageFont.truetype(str(path), size)


def sticker(label, icon, colour, target, angle):
    canvas = Image.new('RGBA', (420, 180), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((14, 18, 406, 164), radius=38, fill=(10, 8, 20, 226),
                           outline='white', width=10)
    draw.rounded_rectangle((22, 26, 398, 156), radius=31, outline=colour, width=7)
    emoji_font = font(Path(r'C:\Windows\Fonts\seguiemj.ttf'), 54)
    text_font = font(Path(r'C:\Windows\Fonts\msjhbd.ttc'), 43)
    try:
        draw.text((38, 57), icon, font=emoji_font, embedded_color=True, anchor='lm')
    except TypeError:
        draw.text((38, 57), icon, font=emoji_font, fill='white', anchor='lm')
    draw.text((122, 90), label, font=text_font, fill='white', stroke_width=3,
              stroke_fill='black', anchor='lm')
    if angle:
        canvas = canvas.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
    canvas.save(target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source, output = Path(args.input).resolve(), Path(args.output).resolve()
    assets = output.parent / (output.stem + '_特效素材')
    assets.mkdir(parents=True, exist_ok=True)
    inputs, chains, last = [], [], '[0:v]'
    for index, (start, end, label, icon, colour, x, y, angle) in enumerate(EVENTS, 1):
        asset = assets / f'{index:02d}.png'
        sticker(label, icon, colour, asset, angle)
        inputs += ['-loop', '1', '-i', str(asset)]
        # Fast pop-in, a gentle pulse, then a short fade-out.
        duration = end - start
        chains.append(
            f'[{index}:v]format=rgba,scale=420:180,'
            f'fade=t=in:st=0:d=0.12:alpha=1,'
            f'fade=t=out:st={duration - 0.20:.3f}:d=0.20:alpha=1,'
            f'setpts=PTS+{start:.3f}/TB[fx{index}]')
        out = f'[v{index}]'
        chains.append(
            f"{last}[fx{index}]overlay=x='{x}+8*sin(7*t)':y='{y}+6*cos(6*t)':"
            f"enable='between(t,{start:.3f},{end:.3f})':eof_action=pass{out}")
        last = out
    filter_complex = ';'.join(chains)
    subprocess.run([
        'ffmpeg', '-y', '-i', str(source), *inputs,
        '-filter_complex', filter_complex + f';{last}setsar=1[final]', '-map', '[final]', '-map', '0:a?',
        '-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq', '-rc', 'vbr',
        '-cq', '18', '-b:v', '0', '-c:a', 'copy', '-r', '30',
        '-t', '125.000', '-movflags', '+faststart', str(output)
    ], check=True)
    print(output)


if __name__ == '__main__':
    main()
