# Release checklist

Require every item before calling an output final:

- `專案狀態.json` resolves rule precedence; the latest explicit creator instruction wins and clip exceptions do not leak into later videos.
- The previous approved output remains preserved. The current render uses a new `vNN` directory and locked caption/framing/chat/audio contracts changed only where explicitly requested.
- `變更影響稽核.md` covers video, audio, SRT, chat/teaching cards, timer, face tracking, chapters, and publish metadata after every timeline change.
- Authorized source and preserved source URL.
- Genuine source resolution at least 1920×1080; no upscaled low-resolution input.
- Title/description-derived terminology brief completed and later evidence-corrected.
- Whisper or supplied subtitles proofread cue-by-cue by the current large language model.
- Taiwan Traditional Chinese, names, Japanese/English terms, punctuation, and semantic segmentation audited.
- Captions appear only during audible host speech.
- Each Short has an independently understandable setup, development, payoff or conclusion, and clean exit; the first and final 10 seconds plus every internal jump cut were reviewed in real time.
- No final keep map was generated solely from subtitle boundaries plus fixed padding.
- Locked PNG caption style unchanged: `y=210`, 138 px Microsoft JhengHei Bold, 7–8 characters per line, two lines maximum, white-to-`#9169CD`, 15 px white rim, 7 px black keyline.
- Face framing targets canvas `x=540` from the two-eye midpoint or validated manual landmarks—not the sprite/crop centre—and covers start, midpoint, end, every cut, and motion extremes.
- `臉部置中稽核.json` passes: median centre error `<=24 px`, 95th-percentile error `<=48 px`, and left/right visible-head margin asymmetry `<=10%`; automatic-tracking failure was resolved with reviewed manual keyframes rather than a silent fixed-crop fallback.
- Tracking is stable: no micro-jitter, implausible pan speed, or lock onto UI, mascot, pet, chat, or background features; cuts and reacquisitions were sampled.
- Every direct chat-dependent reply audited; native boxes included where readable. Any AI-reconstructed card is generated separately from that livestream's own card/frame, evidence-backed, labeled reconstructed, checked character-by-character, and free of baked checkerboard backgrounds.
- Every speech gap at least 0.8 seconds reviewed; all time-dependent assets remapped after cuts.
- Uncaptioned 1080×1920 master retained and used as the exact source for the captioned version.
- Final files pass FFprobe for 1080×1920, 30 fps, SAR 1:1, H.264 video, audio, duration, and nonzero size.
- `音訊驗收.json` records integrated loudness and true peak; target is `-16` to `-14 LUFS` with true peak `<=-1 dBTP`, or a documented creator-approved exception. Speech remains intelligible and effects do not mask line starts or punchlines.
- Shorts obstruction review covers top/notch, right controls, and bottom metadata; no important face, caption, card, timer, health bar, hand, or teaching content is hidden.
- `待確認項目.md` contains no unresolved release blocker; remaining non-blocking uncertainties are disclosed.
- `發布資料包.md` includes title, hashtags, description, chapters/timecodes, pinned-comment suggestion, thumbnail text candidates, Shorts title, relevant terminology note, and source link.
- `發布驗收報告.md` records source/output specs, version, changed scope, transcription/LLM status, subtitle/chat/pause/face/audio/safe-zone results, uncertainty count, samples, and differences from the previous approved version.
- Visual samples cover an ordinary subtitle, two-line subtitle, silent interval, face-tracking extremes, and every chat card.

Create a proofreading marker after the human/LLM audit:

```json
{
  "llm_proofread": true,
  "traditional_chinese_audited": true,
  "model": "current large language model",
  "notes": "Uncertain cues resolved against audio and context."
}
```

Then run `scripts/validate-release.py` with the source, every final Short, every final SRT, and the marker.
