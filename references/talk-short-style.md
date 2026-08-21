# Talk Short House Style

Use this design by default for talk-focused VTuber Shorts. Change it only when the user explicitly asks for a different look.

## Canvas and framing

- Render 1080×1920 H.264/AAC.
- Always render and retain an uncaptioned vertical master before creating caption assets or the captioned version. Validate the master at 1080×1920, 30 fps, square pixels (SAR 1:1), with audio and the expected duration. Build the captioned Short by overlaying captions and dialogue badges onto this exact master; never recrop the horizontal source independently for the captioned version.
- Store masters in the sibling `shorts_無字幕` folder with the suffix `_直式_無字幕.mp4`. Store captioned outputs in `shorts` with the suffix `_直式.mp4`.
- Fill the frame with the original scene; do not add a blank title panel.
- Preserve the approved close, full-frame character crop; do not replace it with a smaller character over a blurred background.
- Inspect representative frames across the whole clip, including the most extreme left/right lean. For moving Live2D characters, run `scripts/track-vtuber-head.py` and render with `--tracking-json`: use the two-eye midpoint as the framing centre, validate/reacquire it against the rigid hair ornament, follow the surrounding left/right hair and face feature field with optical flow, and smooth the resulting per-frame crop path with a dead zone and speed limit. Treat a large strongly validated jump as an editorial cut and restart smoothing immediately on the new shot. Use manual `--crop-keyframes` only as a fallback when automatic tracking cannot be validated.
- Typical talk-short commands are `python scripts/track-vtuber-head.py --input <horizontal.mp4> --output <tracking.json> --cuts <seconds>` followed by `python scripts/render-talk-short.py --input <horizontal.mp4> --srt <captions.srt> --output <captioned.mp4> --no-caption-output <master.mp4> --title <title> --tracking-json <tracking.json>`.
- Retain both eyes and the intended chest framing by following the character horizontally rather than shrinking the entire composition.
- Use `--layout gameplay` only when the highlight's actual topic and payoff depend on gameplay. A game window merely being visible in the source does not make an AI story, programming discussion, or general chat a gameplay Short. For gameplay highlights, reserve the upper 608 px (about one third of the 9:16 canvas) for the game and place the enlarged host below. For the approved Mahjong Soul 1920×1080 layout, use approximately `crop=1380:776:20:174`: exclude the stream title/header and retain the player's complete hand at the bottom. In the 2026-08-11 Mahjong Soul source layout, the host is on the far right: use approximately `crop=640:1080:1280:0`, scale to `1080:1822`, then crop the lower host panel with `crop=1080:1312:0:510`. Do not reuse the generic `crop-x=600` host crop for this layout; it captures the table instead of the VTuber. Reconfirm both table and host bounds from a representative source frame whenever the channel layout changes. Use `--layout talk` for 雜談, AI stories, programming topics, or desktop-focused segments.
- Inspect representative frames before selecting the layout; do not hide meaningful gameplay behind a full-height character crop.

## Caption typography

- Use Microsoft JhengHei Bold (`msjhbd.ttc`) at 138 px.
- Use 7–8 CJK characters per line and at most two lines. Any cue longer than 16 visible characters must be split into the next timed cue using punctuation, a speech pause, and semantic phrasing; never create a third line.
- Center captions in the upper safe area with 24 px line spacing.
- Lock talk captions to `y=210`. Use only the transparent PNG gradient-caption path in `scripts/render-talk-short.py`; generic ASS/libass rendering is not an acceptable fallback.
- Treat the renderer's `APPROVED_CAPTION_STYLE` dictionary as a release contract. Position, Microsoft JhengHei Bold font, 138 px nominal size, 8-character line width, 16-character cue limit, two-line maximum, 15 px white outer rim, 7 px black inner keyline, and host white-to-wisteria gradient must match. If any value differs without the creator's explicit approval, stop rather than render a final file.
- Render every line with its own vertical gradient so every glyph reads as top-white to bottom-color. Never apply one gradient across the entire multi-line caption block.
- Draw layers from outside to inside:
  1. 15 px white outer rim.
  2. 7 px black inner keyline.
  3. Gradient glyph fill.
- Do not add a background box, offset shadow, thick underprint, or full-block gradient.

## Speaker colors

- Host speech: `#FFFFFF` at the top to wisteria `#9169CD` at the bottom.
- Quoted speech, another speaker, or relayed AI dialogue: `#FFFFFF` at the top to coral pink `#FF91AE` at the bottom.

## AI and quoted-dialogue badge

- Do not show a badge during ordinary host speech.
- Show the circular badge only for another speaker, quoted dialogue, or relayed AI dialogue.
- For AI dialogue, use `assets/ai-dialogue-logo.png` inside the circle.
- Keep the pink circular rim and place the badge at the top center without covering caption text.
- In a hand-reviewed SRT, prefix a relayed AI cue with `[[AI]]` or other quoted speech with `[[QUOTE]]`. These are control markers: the renderer must hide them from the visible caption while applying the quoted-speaker gradient and circular badge.

## Caption timing

- Display captions only during audible speech.
- For automatic transcription, require Faster Whisper word timestamps. Set each cue start from its first timed word and its end from its last timed word; do not use continuous sentence boundaries inherited from a long-video SRT.
- Detect silence at roughly `-42 dB` for at least `0.30 s` and suppress captions during those intervals.
- Bias each caption onset about `0.15 s` after the transcript boundary so text never appears before speech.
- End captions about `0.08 s` before the transcript boundary when practical.
- Never stretch a previous sentence through a silent pause.
- For Chinese/Japanese mixed speech, transcribe each selected clip independently with multilingual detection instead of forcing `zh`. Preserve spoken Japanese as Japanese text when confidently recognized.
- Derive every display cue directly from word timestamps, split at pauses of roughly 0.38 seconds, punctuation, or the 16-character limit. Do not crop cues out of a long-video sentence-level SRT.

## Validation

- Inspect at least one ordinary host line, one quoted/AI line, and one silent interval.
- Verify that the white rim remains visible, the black keyline separates the gradient from bright backgrounds, and the character crop does not remove both eyes or the intended chest framing.
