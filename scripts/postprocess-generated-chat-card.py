import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def exterior_background_mask(rgb):
    # Image generators may render a transparency checkerboard as real pixels.
    # Remove only neutral, bright components connected to the canvas border so
    # white message text enclosed by the dark card remains opaque.
    high = rgb.max(axis=2)
    low = rgb.min(axis=2)
    candidate = ((low >= 198) & ((high - low) <= 28)).astype(np.uint8)
    count, labels = cv2.connectedComponents(candidate, connectivity=8)
    border_labels = set(labels[0, :]) | set(labels[-1, :]) | set(labels[:, 0]) | set(labels[:, -1])
    border_labels.discard(0)
    mask = np.isin(labels, list(border_labels)).astype(np.uint8) * 255
    return cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)


def main():
    parser = argparse.ArgumentParser(description='Clean a per-message AI-reconstructed chat card for compositing.')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--cover', help='Optional x:y:w:h area to repaint from its top-left background sample')
    parser.add_argument('--text', help='Exact replacement text for --cover')
    parser.add_argument('--font-size', type=int, default=150)
    parser.add_argument('--text-x', type=int)
    parser.add_argument('--text-y', type=int)
    args = parser.parse_args()

    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    rgb = np.array(Image.open(source).convert('RGB'))
    alpha = 255 - exterior_background_mask(rgb)
    image = Image.fromarray(np.dstack([rgb, alpha]))

    if args.cover:
        if args.text is None or args.text_x is None or args.text_y is None:
            raise ValueError('--cover requires --text, --text-x and --text-y')
        x, y, width, height = map(int, args.cover.split(':'))
        draw = ImageDraw.Draw(image)
        sample = image.getpixel((max(0, x - 10), max(0, y + height // 2)))
        draw.rectangle((x, y, x + width, y + height), fill=sample)
        font = ImageFont.truetype(r'C:\Windows\Fonts\msjhbd.ttc', args.font_size)
        draw.text((args.text_x, args.text_y), args.text, font=font, fill=(255, 255, 255, 255))

    bbox = image.getbbox()
    if not bbox:
        raise RuntimeError('Generated card became empty after background cleanup.')
    image.crop(bbox).save(output)
    print(output)


if __name__ == '__main__':
    main()
