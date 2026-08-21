# Claude Video design notes

Reference: <https://github.com/bradautomates/claude-video> (MIT License, copyright Bradley Bonanno).

Ideas incorporated into this skill:

- Try native/automatic captions before downloading or paying for transcription.
- Fall back to Whisper only when captions are absent or unusable.
- Combine timestamped transcript evidence with sampled visual frames.
- Budget visual frames for long videos instead of sampling at a fixed high rate.
- Use a sparse whole-video overview, then dense focused passes on candidate moments.
- Keep timestamps attached to extracted frames so editorial claims remain auditable.

This skill adds a separate editorial/rendering layer: highlight ranking, cut-boundary refinement, per-clip subtitles, 9:16 rendering, and compilation output. Its scripts are independently implemented; do not copy substantial upstream code without retaining the upstream MIT notice.
