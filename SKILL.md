---
name: youtube-highlight-shorts
description: Download an authorized YouTube video, obtain or generate a timestamped transcript, proofread subtitles with the current large language model, analyze compelling highlights, remove dead air, track and center a VTuber face, create 9:16 Shorts with locked caption styling, extract or evidence-reconstruct native viewer chat cards, and concatenate a compilation. Use when a user supplies a YouTube URL or creator master and asks for highlights, clips, Shorts, 精華, 短影片, 逐字稿, 字幕, 聊天室字卡, or an automated livestream-to-short-video workflow.
---

# YouTube Highlight Shorts

Turn one authorized YouTube video into an auditable set of transcripts, selected highlights, horizontal clips, vertical Shorts, subtitle files, and a compilation.

## Safety and scope

- Process only content the user owns, controls, or is authorized to download and reuse.
- Do not bypass DRM, paywalls, private-video access controls, or platform restrictions.
- Preserve attribution and the source URL in `精華時間碼.md`.
- Treat automatic highlight selection as editorial assistance. Inspect outputs before publishing.

## Setup

Read `references/setup.md` before the first run on a machine. Use PowerShell 7 or newer and run `scripts/check-dependencies.ps1`; do not continue with missing tools or Python modules.

## Workflow

1. Confirm the URL and output directory. If the user gives no directory, create `<channel-or-title>_精華_<YYYYMMDD>` under the current workspace. Read `references/project-governance.md`, resolve global/series/clip-specific rule precedence, and create `<output>/專案狀態.json` before editing. Preserve the last approved version and lock its caption, framing, chat-card, and audio contracts; a narrowly requested change must not mutate unrelated approved properties.
2. Run `scripts/check-dependencies.ps1`. Use PowerShell 7 or newer.
3. Require a genuine 1080p-or-higher source before editing:
   - Run `yt-dlp -F <url>` and confirm that a video stream with height `>=1080` is available.
   - Download the best 1080p-or-higher video stream plus the best audio stream and merge them. Prefer 1080p60 when available.
   - Verify the downloaded source with `ffprobe`; require width `>=1920` and height `>=1080`. Do not treat an upscaled 360p or 720p file as 1080p.
   - If YouTube has not finished HD processing or no genuine 1080p stream is available, stop before rendering and retry later or request the creator's original master. Never silently continue with a lower-resolution source.
   - Then run or adapt `scripts/prepare-video.ps1 -Url <url> -OutputDir <dir>` to obtain metadata, available subtitles, and an audio track without replacing the verified HD source with a lower-quality fallback.
4. Build a provisional terminology brief before transcription:
   - Read the video title first, then the description, chapters, tags, channel context, and clearly readable on-screen text to infer likely people, places, games, products, organizations, technical terms, foreign-language phrases, and recurring community vocabulary.
   - Record canonical Taiwan Traditional Chinese spellings plus relevant Japanese, English, romanized, abbreviated, and common homophone variants in `<output>/術語表.md`.
   - Use the terminology brief as a transcription and proofreading hint, not as ground truth. Accept a candidate term only when the audio, sentence meaning, or visible evidence supports it; never force a title-derived term into unrelated dialogue.
   - Expand the brief when the transcript reveals additional recurring terms, and use the same canonical spelling consistently across every clip and SRT.
5. Produce a timestamped transcript:
   - Prefer creator-provided Traditional Chinese subtitles.
   - Otherwise prefer available Chinese subtitles and normalize to Traditional Chinese when practical.
   - Otherwise transcribe `source-audio.wav` with an installed Whisper-compatible engine. Preserve both `.srt` and plain `.txt`.
   - When `faster-whisper` is installed, use word timestamps. For Chinese/Japanese mixed streams, transcribe each selected clip independently with `scripts/transcribe-highlight-batch.py --language auto`; do not force Chinese because it corrupts Japanese speech. Build display cues from timed words rather than cropping a long-video sentence SRT.
   - Never invent dialogue when recognition is uncertain.
6. Proofread every transcript and SRT with the current large language model before highlight selection or rendering:
   - Review the text cue by cue against the audio and surrounding context; never use raw Whisper output directly in a published video.
   - Consult `術語表.md`, then convert Chinese dialogue to Taiwan Traditional Chinese and correct Simplified Chinese, homophone errors, missing or duplicated words, punctuation, segmentation, names, places, and domain-specific terms.
   - Preserve word-level timing evidence. Adjust cue boundaries only when needed for readable phrasing and audible speech; do not detach text from the spoken audio.
   - Do not invent uncertain dialogue. Mark unclear words for manual review and resolve them before final rendering.
   - Run a final text audit on every SRT and reject files that still contain unintended Simplified Chinese, obvious recognition errors, or cues that violate the caption line limits.
7. Run `scripts/extract-review-frames.py --video <dir>/source.mp4 --output <dir>/review-frames --mode overview`. Read the timestamp manifest and inspect representative frames together with the proofread transcript.
8. Read `references/highlight-selection.md`, inspect transcript semantics plus audio and visual evidence, then write a provisional `highlights.json` following its schema.
   - Before rendering, audit each candidate as a complete story arc: identify the initiating question or setup, the host's first dependent response, the development, the payoff or conclusion, and a clean exit.
   - If a clip begins with a pronoun, answer, correction, or punchline whose referent is outside the cut, move the start backward until the cause is audible or visible. A title card alone does not replace missing conversational setup.
   - Reject or expand a candidate whose opening, middle, or ending cannot be understood without the surrounding livestream.
9. Run the frame script again with `--mode highlights --highlights <dir>/highlights.json` to densely inspect each candidate. Adjust cut boundaries and reject visually weak or misleading candidates.
10. Audit chat-triggered topics before creating chat cards:
   - Work backward from the host's first audible read or reply and identify the exact message that opened the topic. Record the original author, verbatim message, source timestamp, clip-relative timestamp, and evidence source in `<output>/聊天室觸發留言稽核.md`.
   - Distinguish the initial trigger from later reactions, corrections, jokes, and follow-up messages. Do not label a merely related message as the topic trigger.
   - If the host opened the topic before any matching chat message appeared, mark it as host-initiated and do not add a misleading trigger card.
   - When the broadcast layout already displays player messages as native chat boxes, crop the exact visible box from the original 1080p source frame and reuse that bitmap, preserving its avatar or level badge, username, colors, border, and message text. A typed or reconstructed card is not an acceptable substitute.
   - If the target box is temporarily obscured or clipped, search adjacent source frames for a fully readable appearance. If no usable native box exists, leave the card unresolved unless the user explicitly authorizes reconstruction. When authorized, generate each card separately from that livestream's own corresponding card/frame and verified replay evidence; never use one generic chat template. Inspect every generated glyph and label the result reconstructed.
   - Show the trigger card shortly before the host reads or begins replying to it. Preserve the original wording when reliable evidence exists; do not replace it with an editorial paraphrase.
   - If the trigger appears to come from another platform and cannot be authenticated from the source frame or replay, mark it unresolved and retain the source frame for manual review rather than inventing an author or message.
   - Read `references/chat-cards.md`. Use `scripts/crop-native-chat-card.py` for deterministic source-frame crops and `scripts/overlay-native-chat-cards.py` to apply the verified, tightened-time manifest.
11. Audit every direct chat response, not only the first topic trigger:
   - Review the full proofread transcript and source video for moments where the host reads, quotes, answers, corrects, jokes about, or clearly reacts to a player message.
   - For each such moment, locate and crop the corresponding native player-message box. Include follow-up messages whenever the host's next sentence depends on them; do not limit chat extraction to one card per highlight.
   - Group rapid replies to the same message so the same card is not flashed repeatedly. Keep each card readable long enough for its text length, normally about 2.5–6 seconds, and align it just before or at the start of the dependent spoken reply.
   - Write a per-highlight chat-response audit with the number of direct replies, cards included, unresolved source boxes, and any deliberately omitted duplicates. A final Short should not pass when obvious direct chat replies lack their source card.
12. Tighten spoken pacing before caption and chat-card rendering:
   - Use word timestamps, corrected SRT gaps, waveform evidence, and visual continuity to identify intervals with no useful host speech.
   - Remove dead air, waiting, reading-without-payoff, repeated filler, and other non-content pauses when the cut does not damage a reaction, comedic beat, sentence meaning, or visible action.
   - Preserve short natural breathing and intentional comedic timing. As a default review rule, inspect every no-speech gap `>=0.8s`; gaps around `1.2s` or longer should be cut or explicitly justified.
   - Never build final keep intervals mechanically from subtitle cues with one fixed padding value. Such compression can delete the question, the referent of a pronoun, a visible chat trigger, reaction timing, or the bridge between two thoughts. Use transcript semantics and visual continuity to approve every jump cut.
   - Apply the same time-remap to video, audio, SRT cues, native chat-card timing, and face-tracking data. Rebase all timestamps after each removal and verify that no subtitle or chat card drifts out of sync.
   - Write `<output>/停頓刪減稽核.md` listing original interval, removed duration, reason, and retained intentional pauses.
13. Write `精華時間碼.md` with the source, original duration, highlight count, total selected duration, narrative arc, and a table of start/end/duration/title/summary.
14. Run `scripts/render-highlights.py --input-dir <dir> --highlights <dir>/highlights.json`.
15. Before each rerender, update `變更影響稽核.md` for video, audio, SRT, chat cards, teaching cards, timers, face tracking, chapters, and output metadata. Render into a new version directory; never overwrite the last approved output. For every Short, render and verify the uncaptioned vertical master first. Only after its crop, aspect ratio, audio, and duration pass validation, render the captioned Short from that exact master. Never build the two versions from separate crop calculations.
16. Read `references/release-checklist.md`. Create `字幕校正狀態.json` only after completing the language-model and Traditional Chinese audit. Verify media with `ffprobe`, measure program loudness/true peak, inspect Shorts UI safe zones and tracking stability, and sample start/middle/end, every cut, motion extreme, and card. Record uncertainties in `待確認項目.md`; unresolved release blockers stop delivery.
17. Complete `發布資料包.md` and `發布驗收報告.md`, update `專案狀態.json`, then run `scripts/validate-governance.py --state <output>/專案狀態.json` and `scripts/validate-release.py`. Report source/output specs, release version, transcription/LLM status, chat coverage, pause removal, face/audio/safe-zone results, uncertainty count, and exact differences from the previous approved version.

## Editing defaults

- Favor self-contained moments with setup, payoff, and a clean exit; usually 30–180 seconds.
- Treat narrative completeness as a release gate: every Short must make sense from its first frame without the viewer knowing the previous livestream sentence. Review the first 10 seconds and the final 10 seconds in real time, then review every internal jump cut for missing referents or abrupt topic changes.
- Treat genuine 1080p input, completed language-model subtitle proofreading, the approved caption-style contract, and face-centred symmetric framing as mandatory release gates. Do not render final deliverables when any gate fails.
- Add 0.5–2 seconds of conversational context when cuts feel abrupt, without overlapping adjacent clips unnecessarily.
- Keep horizontal clips at source resolution and frame rate where feasible.
- For every 1080×1920 Short, align the host's facial centre—not the character sprite box or a fixed source crop—to canvas `x=540`. Use the two-eye midpoint when visible; when eyes are obscured, use validated facial/head landmarks or manually reviewed crop keyframes. Audit the start, midpoint, end, every editorial cut, and each left/right motion extreme. Require median absolute centre error `<=24 px`, 95th-percentile error `<=48 px`, and left/right visible-head margin asymmetry `<=10%` of visible head width. Automatic tracking failure must stop release or trigger manual keyframes; never silently fall back to one fixed crop. Save `臉部置中稽核.json` and pass it through `scripts/validate-face-centering.py` before caption rendering.
- Render Shorts as 1080×1920 H.264/AAC. Use `scripts/render-talk-short.py` and preserve the approved house style in `references/talk-short-style.md` unless the user explicitly requests a different design. The caption path is locked to the renderer's `APPROVED_CAPTION_STYLE` contract: do not replace its transparent PNG gradient layers with ASS/libass subtitles, editor defaults, or ad-hoc `force_style` values. A mismatch in caption position, font, gradient, outlines, line width, or line count must stop the release instead of silently producing a fallback. The script must first create `shorts_無字幕/NN_title_直式_無字幕.mp4`, validate it, and then use that file as the picture-and-audio source for `shorts/NN_title_直式.mp4`. Always retain both files. Classify by the highlight's topic, title, transcript, and payoff—not by whether a game happens to be visible in the source layout. Use `--layout talk` for 雜談, AI stories, programming discussions, and other host-led topics. Use `--layout gameplay` only when understanding the selected moment depends on the game, so the upper third preserves the game view/UI and the lower area carries the enlarged host. Avoid blind center-crops that remove faces, captions, or gameplay UI.
- Keep each segment's SRT timestamps relative to the segment. Treat the uncaptioned master as mandatory even when the user ultimately wants subtitles.
- Chat cards identify the real conversational cause: crop and display the native player-message box already present in the source layout, align it to the start of the host's read/reply, and omit the card when the topic was host-initiated. A later related message may be shown only as a clearly labeled follow-up, never as the trigger. Do not redraw a visible source chat box as plain text.
- Chat-card frequency follows actual conversational dependency rather than a fixed per-video quota: every clearly identifiable player message that the host directly responds to is a card candidate, including mid-topic follow-ups.
- Review every speech gap of at least 0.8 seconds and tighten non-content pauses. Never cut solely from an amplitude threshold; protect sentence meaning, reaction timing, jokes, and visual continuity.
- Normalize filenames as `NN_title.mp4`, `NN_title_直式_無字幕.mp4`, `NN_title_直式.mp4`, and `NN_title.srt` while retaining readable Traditional Chinese.
- Concatenate in editorial order into `精華合輯.mp4`.

## Project governance

Treat `references/project-governance.md` as a mandatory release contract:

- Apply rules in this order: latest explicit clip instruction, approved clip exception, series contract, then global contract. A clip exception never becomes the next video's default.
- Freeze approved caption, framing, chat-card, and audio settings. Change only creator-requested properties; verify locked properties after every rerender.
- Use smooth face tracking with a dead zone and speed limit. Reject locks on UI, mascots, pets, chat, or background features and review reacquisition after cuts.
- Target integrated loudness around `-16` to `-14 LUFS` and true peak `<=-1 dBTP`, unless a documented creator-approved exception applies. Speech must remain intelligible.
- Keep important faces, captions, cards, timers, health bars, hands, and teaching content outside top/notch, right-control, and bottom-metadata obstruction zones.
- Preserve approved versions. Use explicit `vNN` candidates and promote to `final` only after all gates pass.

## Output contract

Create:

```text
<output>/
  source.info.json
  source.mp4
  source-audio.wav
  術語表.md
  逐字稿.txt
  逐字稿.srt
  字幕校正狀態.json
  臉部置中稽核.json
  highlights.json
  精華時間碼.md
  專案狀態.json
  變更影響稽核.md
  待確認項目.md
  音訊驗收.json
  發布資料包.md
  發布驗收報告.md
  聊天室觸發留言稽核.md
  聊天室回覆覆蓋率稽核.md
  停頓刪減稽核.md
  clips/NN_title.mp4
  shorts_無字幕/NN_title_直式_無字幕.mp4
  shorts/NN_title_直式.mp4
  字幕SRT/NN_title.srt
  精華合輯.mp4
```

Retain intermediate downloads until verification succeeds. Do not delete source media unless the user explicitly requests cleanup.

## Design reference

The transcript-first and budgeted visual-review design is informed by `bradautomates/claude-video`. Read `references/claude-video-notes.md` when maintaining the analysis layer or changing frame-budget behavior.

For talk-focused VTuber Shorts, read `references/talk-short-style.md` before changing framing, captions, speaker colors, dialogue badges, or timing. Treat it as the default approved visual system.

Read `references/project-governance.md` at project start, before every rerender, and before release. It defines precedence, approval locks, impact remapping, tracking/audio QA, safe zones, uncertainty handling, version preservation, publishing metadata, and final evidence reporting.
