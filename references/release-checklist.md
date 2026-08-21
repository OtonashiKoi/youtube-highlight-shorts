# Release checklist

Require every item before calling an output final:

- Authorized source and preserved source URL.
- Genuine source resolution at least 1920×1080; no upscaled low-resolution input.
- Title/description-derived terminology brief completed and later evidence-corrected.
- Whisper or supplied subtitles proofread cue-by-cue by the current large language model.
- Taiwan Traditional Chinese, names, Japanese/English terms, punctuation, and semantic segmentation audited.
- Captions appear only during audible host speech.
- Each Short has an independently understandable setup, development, payoff or conclusion, and clean exit; the first and final 10 seconds plus every internal jump cut were reviewed in real time.
- No final keep map was generated solely from subtitle boundaries plus fixed padding.
- Locked PNG caption style unchanged: `y=210`, 138 px Microsoft JhengHei Bold, 7–8 characters per line, two lines maximum, white-to-`#9169CD`, 15 px white rim, 7 px black keyline.
- Face framing follows the two-eye midpoint across representative motion extremes.
- Every direct chat-dependent reply audited; native boxes included where readable. Any AI-reconstructed card is generated separately from that livestream's own card/frame, evidence-backed, labeled reconstructed, checked character-by-character, and free of baked checkerboard backgrounds.
- Every speech gap at least 0.8 seconds reviewed; all time-dependent assets remapped after cuts.
- Uncaptioned 1080×1920 master retained and used as the exact source for the captioned version.
- Final files pass FFprobe for 1080×1920, 30 fps, SAR 1:1, H.264 video, audio, duration, and nonzero size.
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
