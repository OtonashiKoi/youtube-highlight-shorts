# Project governance and release control

Read this file at project start, before every rerender, and before release.

## Rule precedence

Resolve conflicts from highest to lowest:

1. Latest explicit creator instruction for the current clip.
2. Previously approved exception for the current clip.
3. Approved series/layout contract.
4. Global skill contract.

A clip exception never becomes the next video's default. Record resolved values and scope in `專案狀態.json`. Never infer an exception that changes unrelated approved properties.

## Approval locks

After creator approval, freeze these contracts with settings, a reference frame, and a hash when practical:

- Caption position, font, size, gradient, outlines, line limits, and segmentation.
- Framing/layout, face-centre target, scale, and safe crop.
- Native/reconstructed chat-card appearance, placement, and timing rules.
- Program loudness, effect assets, effect gain, and ducking behavior.

For a narrow request such as “fix this subtitle” or “lower this sound,” mutate only that contract. Compare every locked property after rerender. A regression stops release.

## Change-impact matrix

Update `變更影響稽核.md` before rendering:

| Change | Mandatory consumers to recheck |
|---|---|
| Cut/start/end/dead-air map | video, audio, SRT, chat, teaching cards, timer, tracking, chapters/timecodes |
| Crop/layout/tracking | uncaptioned master, captioned output, card collision, safe zones |
| Subtitle text/timing | SRT, caption layers, silence coverage, screenshots |
| Chat/teaching card | evidence, author/text, timing, collision, safe zones |
| Audio/effect | mix, loudness, true peak, speech intelligibility, sync |

Use one time-remap for all time-dependent assets. Never patch only the visible output while leaving source manifests stale.

## Tracking stability

- Follow face motion with a dead zone and speed limit; ignore Live2D micro-jitter.
- Reacquire immediately after editorial cuts or strongly validated layout jumps.
- Reject locks on UI, mascots, pets, chat, game objects, or background features.
- Review start, middle, end, every cut, reacquisition, and left/right motion extreme.
- Use manual keyframes when automatic evidence is weak. Do not release an unvalidated fixed-crop fallback.

## Audio release standard

- Target integrated program loudness around `-16` to `-14 LUFS` and true peak `<=-1 dBTP`.
- Allow a different target only with a documented creator/platform exception.
- Keep speech intelligible above game/background audio.
- Do not mask line starts, punchlines, or reactions with notification effects.
- Inspect jump cuts for clicks, abrupt noise-floor changes, missing channels, and sync drift.
- Store method, integrated LUFS, true peak, exception, and listening notes in `音訊驗收.json`.

## Platform obstruction map

Review a 1080×1920 composite showing top title/notch/status area, right reaction/comment/share controls, and bottom channel/title/description area. Keep important faces, captions, cards, timers, health bars, player hands, and teaching content outside these zones. User-approved platform measurements override generic guides and belong in the series contract.

## Uncertainty ledger

Write `待確認項目.md` with timestamp, clip, issue, evidence, confidence, owner, and release impact for unclear speech/terminology, unverified chat evidence, ambiguous context/cuts, and uncertain asset/licensing evidence. Never hide uncertainty by inventing content. Resolve every release blocker before `final`.

## Version preservation

- Render material changes into a new `vNN` directory.
- Preserve the previous approved version until the creator approves its replacement.
- Promote a candidate to `final` only after every gate passes.
- Subtitle-only changes must not recrop video; audio-only changes should remix/remux without re-encoding video when practical.
- Record parent version, changed scope, output hashes, and approval state in `專案狀態.json`.

## Publishing package

Write `發布資料包.md` with YouTube title, Shorts title, hashtags, description, chapters/timecodes, source link, pinned-comment suggestion, thumbnail text candidates, and relevant terminology/educational notes. Keep every claim consistent with the edited clip.

## Release evidence report

Write `發布驗收報告.md` with source/output specs, release version, exact change scope, terminology/transcription/LLM status, story-arc review, subtitle/chat/pause/face/audio/safe-zone results, uncertainty count, sample paths, hashes, and differences from the previous approved version.

Validate `專案狀態.json` with `scripts/validate-governance.py`. A pass confirms evidence fields are present; it does not replace visual/listening review.
