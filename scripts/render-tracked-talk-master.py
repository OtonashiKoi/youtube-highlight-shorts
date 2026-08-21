import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np


def probe_audio_duration(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
        check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--tracking-json', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--fps', type=float, default=30.0)
    args = parser.parse_args()

    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    tracking = json.loads(Path(args.tracking_json).read_text(encoding='utf-8'))
    times = np.asarray(tracking['times'], dtype=np.float64)
    crop_x = np.asarray(tracking['crop_x'], dtype=np.float64)
    duration = probe_audio_duration(source)
    output.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(source))
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
    # Exact combined equivalent of the approved close crop:
    # crop 680x1080 -> scale 1580x2509 -> crop 1080x1920 at 260,310.
    inner_x, inner_y, inner_w, inner_h = 112, 133, 465, 827
    command = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', '1080x1920', '-r', f'{args.fps:g}', '-i', 'pipe:0',
        '-i', str(source), '-map', '0:v:0', '-map', '1:a?',
        '-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq',
        '-rc', 'vbr', '-cq', '19', '-b:v', '0', '-c:a', 'aac', '-b:a', '160k',
        '-t', f'{duration:.3f}', '-movflags', '+faststart', str(output)]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    output_index = 0
    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            source_time = frame_index / source_fps
            expected_index = int(np.floor(source_time * args.fps + 1e-6))
            if expected_index >= output_index:
                tracked_x = float(np.interp(source_time, times, crop_x))
                left = int(round(tracked_x + inner_x))
                top = inner_y
                left = max(0, min(frame.shape[1] - inner_w, left))
                top = max(0, min(frame.shape[0] - inner_h, top))
                close = frame[top:top + inner_h, left:left + inner_w]
                vertical = cv2.resize(close, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
                proc.stdin.write(vertical.tobytes())
                output_index += 1
            frame_index += 1
    finally:
        cap.release()
        if proc.stdin:
            proc.stdin.close()
        code = proc.wait()
    if code:
        raise SystemExit(code)
    print(output)


if __name__ == '__main__':
    main()
