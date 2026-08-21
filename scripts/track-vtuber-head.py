import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def clamp(value, low, high):
    return max(low, min(high, value))


def purple_candidates(frame, search):
    """Find the purple flower/hair ornament that moves rigidly with the head."""
    x0, y0, x1, y1 = search
    roi = frame[y0:y1, x0:x1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array((115, 55, 35)), np.array((175, 255, 255)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    candidates = []
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        cx, cy = centroids[index]
        cx, cy = cx + x0, cy + y0
        if 35 <= w <= 105 and 45 <= h <= 135 and 900 <= area <= 5200 and x0 + x < 1190:
            # Prefer the flower-sized component. When tracking is active, spatial
            # continuity prevents purple UI elements from stealing the lock.
            shape_score = abs(w - 72) * 0.8 + abs(h - 86) * 0.6 + abs(area - 3450) / 80
            candidates.append((shape_score, float(cx), float(cy), int(area)))
    return candidates


def eye_centers(frame):
    """Return candidate midpoints of two cyan irises."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array((75, 70, 70)), np.array((105, 255, 255)))
    mask[:200] = 0
    mask[760:] = 0
    mask[:, :550] = 0
    mask[:, 1260:] = 0
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    candidates = []
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        cx, cy = centroids[index]
        if 10 <= w <= 35 and 8 <= h <= 28 and 80 <= area <= 320:
            candidates.append((float(cx), float(cy), int(area)))
    pairs = []
    for left in candidates:
        for right in candidates:
            dx, dy = right[0] - left[0], abs(right[1] - left[1])
            if 135 <= dx <= 225 and dy <= 50:
                score = abs(dx - 182) + 0.7 * dy - 0.01 * (left[2] + right[2])
                pairs.append((score, (left[0] + right[0]) / 2, (left[1] + right[1]) / 2))
    return pairs


def reacquire_head(frame, search, previous=None):
    """Return the eye midpoint after validating it against the hair ornament."""
    best = None
    for shape_score, flower_x, flower_y, area in purple_candidates(frame, search):
        for eye_score, eye_x, eye_y in eye_centers(frame):
            dx, dy = flower_x - eye_x, flower_y - eye_y
            if not (35 <= dx <= 190 and -360 <= dy <= -120):
                continue
            relation = abs(dx - 105) * 0.65 + abs(dy + 245) * 0.25
            continuity = 0 if previous is None else abs(eye_x - previous[0]) * 0.25 + abs(eye_y - previous[1]) * 0.12
            candidate = (shape_score + eye_score + relation + continuity,
                         eye_x, eye_y, area)
            if best is None or candidate[0] < best[0]:
                best = candidate
    return best


def smooth_path(values, fps, dead_zone=8.0, max_speed=95.0):
    values = np.asarray(values, dtype=np.float64)
    # Fill gaps in each editorial segment before filtering.
    valid = np.flatnonzero(np.isfinite(values))
    if not len(valid):
        raise RuntimeError('No usable head anchors were detected.')
    values[:valid[0]] = values[valid[0]]
    values[valid[-1] + 1:] = values[valid[-1]]
    missing = ~np.isfinite(values)
    values[missing] = np.interp(np.flatnonzero(missing), valid, values[valid])

    # A one-second median suppresses bad measurements, then a damped low-pass
    # gives a natural camera response instead of copying Live2D micro-jitter.
    window = max(3, int(round(fps)) | 1)
    padded = np.pad(values, window // 2, mode='edge')
    median = np.array([np.median(padded[i:i + window]) for i in range(len(values))])
    result = np.empty_like(median)
    result[0] = median[0]
    alpha = 1.0 - np.exp(-1.0 / max(1.0, fps * 0.42))
    step_limit = max_speed / fps
    for index in range(1, len(result)):
        delta = median[index] - result[index - 1]
        if abs(delta) <= dead_zone:
            result[index] = result[index - 1]
        else:
            step = clamp(delta * alpha, -step_limit, step_limit)
            result[index] = result[index - 1] + step
    return result


def smooth_segments(values, fps, break_indices):
    result = np.empty(len(values), dtype=np.float64)
    edges = [0] + sorted(set(break_indices)) + [len(values)]
    for start, end in zip(edges, edges[1:]):
        if end > start:
            result[start:end] = smooth_path(values[start:end], fps)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True, help='JSON tracking data')
    parser.add_argument('--analysis-fps', type=float, default=15.0)
    parser.add_argument('--anchor-offset', type=float, default=345.0,
                        help='Source crop x = eye midpoint x - this value')
    parser.add_argument('--min-crop-x', type=float, default=320.0)
    parser.add_argument('--max-crop-x', type=float, default=660.0)
    parser.add_argument('--cuts', default='', help='Comma-separated editorial cut times in seconds')
    args = parser.parse_args()

    source = Path(args.input).resolve()
    cap = cv2.VideoCapture(str(source))
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / source_fps
    step = max(1, round(source_fps / args.analysis_fps))
    analysis_fps = source_fps / step
    anchors, times, previous = [], [], None
    auto_break_indices = []
    cuts = [float(x) for x in args.cuts.split(',') if x.strip()]
    next_cut = 0
    previous_gray = None
    points = None
    frame_index = 0
    search = (600, 70, 1260, 720)
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % step:
            frame_index += 1
            continue
        time = frame_index / source_fps
        cut_reset = next_cut < len(cuts) and time >= cuts[next_cut] - 1 / analysis_fps
        if cut_reset:
            previous = previous_gray = points = None
            next_cut += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        crop_x = np.nan
        # Track many high-contrast hair/face features after the initial lock.
        # The median optical-flow vector is robust to blinking and mouth motion.
        if previous_gray is not None and points is not None and len(points) >= 10:
            moved, status, _ = cv2.calcOpticalFlowPyrLK(
                previous_gray, gray, points, None,
                winSize=(31, 31), maxLevel=3,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 24, 0.01))
            good_old = points[status.ravel() == 1]
            good_new = moved[status.ravel() == 1]
            if len(good_new) >= 10:
                shift = np.median(good_new - good_old, axis=0).ravel()
                if abs(shift[0]) < 35 and abs(shift[1]) < 28:
                    previous = (previous[0] + float(shift[0]), previous[1] + float(shift[1]))
                    points = good_new.reshape(-1, 1, 2)
                    crop_x = clamp(previous[0] - args.anchor_offset,
                                   args.min_crop_x, args.max_crop_x)
        # The iris pair is a stable head-centre measurement. Use it to correct
        # slow optical-flow drift while the hair feature cloud supplies motion
        # through blinks and expression changes.
        found = reacquire_head(frame, search, previous)
        if found:
            lock_score, eye_x, eye_y, _ = found
            relock_jump = previous is not None and abs(eye_x - previous[0]) > 180 and lock_score < 180
            if relock_jump:
                # A large, strongly validated displacement is an editorial cut,
                # not physical head motion. Jump immediately and keep smoothing
                # isolated on the new shot.
                auto_break_indices.append(len(anchors))
                previous_gray = points = None
                previous = (eye_x, eye_y)
                crop_x = clamp(previous[0] - args.anchor_offset,
                               args.min_crop_x, args.max_crop_x)
            elif previous is None or abs(eye_x - previous[0]) <= 180:
                if previous is None or not np.isfinite(crop_x):
                    previous = (eye_x, eye_y)
                else:
                    previous = (0.72 * previous[0] + 0.28 * eye_x,
                                0.72 * previous[1] + 0.28 * eye_y)
                crop_x = clamp(previous[0] - args.anchor_offset,
                               args.min_crop_x, args.max_crop_x)
        # Reacquire at startup, at editorial cuts, or after optical-flow loss.
        if not np.isfinite(crop_x):
            if found:
                _, cx, cy, _ = found
                previous = (cx, cy)
                crop_x = clamp(cx - args.anchor_offset, args.min_crop_x, args.max_crop_x)
        if previous is not None and (points is None or len(points) < 18 or frame_index % max(step, round(source_fps)) == 0):
            cx, cy = previous
            mask = np.zeros_like(gray)
            left, top = int(clamp(cx - 300, 0, frame.shape[1] - 1)), int(clamp(cy - 390, 0, frame.shape[0] - 1))
            right, bottom = int(clamp(cx + 300, 1, frame.shape[1])), int(clamp(cy + 300, 1, frame.shape[0]))
            mask[top:bottom, left:right] = 255
            points = cv2.goodFeaturesToTrack(gray, maxCorners=140, qualityLevel=0.015,
                                             minDistance=9, mask=mask, blockSize=7)
        previous_gray = gray
        anchors.append(crop_x)
        times.append(time)
        frame_index += 1
    cap.release()

    break_indices = [int(np.searchsorted(times, cut)) for cut in cuts] + auto_break_indices
    smoothed = smooth_segments(anchors, analysis_fps, break_indices)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        'source': str(source),
        'duration': duration,
        'analysis_fps': analysis_fps,
        'times': [round(x, 4) for x in times],
        'crop_x': [round(float(x), 3) for x in smoothed],
        'raw_crop_x': [None if not np.isfinite(x) else round(float(x), 3) for x in anchors],
        'segment_break_indices': sorted(set(break_indices)),
    }, ensure_ascii=False), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
