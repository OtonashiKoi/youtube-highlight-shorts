# Native chat-card workflow

Use only player-message boxes visibly present in the authorized source video unless the creator explicitly requests reconstruction.

1. Find the host's first audible read or dependent reply.
2. Search backward and in adjacent frames for the exact fully readable native box.
3. Record author, verbatim message, source time, clip-relative time, and evidence frame.
4. Crop the bitmap without redrawing its avatar, badge, username, colors, border, or text.
5. Show it shortly before or at the start of the dependent reply, normally for 2.5–6 seconds.

Crop example:

```powershell
python scripts/crop-native-chat-card.py --input source.mp4 --at 00:38:12.500 --crop 760:160:1040:780 --output cards/message.png
```

Overlay manifest:

```json
[
  {"asset": "cards/message.png", "start": 12.25, "end": 17.45}
]
```

Times are relative to the final tightened Short. Apply every pause-removal time map before writing this manifest.

```powershell
python scripts/overlay-native-chat-cards.py --input captioned.mp4 --cards chat-cards.json --output final.mp4
```

If the exact native card exists but is too blurred, compressed, clipped, or covered to read in the final Short, the creator may explicitly authorize an AI reconstruction. Generate each message separately from that livestream's own corresponding card/frame; do not create one generic template and swap text. Preserve the verified viewer name, level/member treatment, name color, frame geometry, and verbatim message. Use the built-in image-generation tool by default, then inspect every glyph. Run `scripts/postprocess-generated-chat-card.py` when the generator bakes a checkerboard into the image or when a verified glyph needs deterministic repair. Label the asset and audit row as reconstructed.

Never infer an unknown name or message from the host's reply. A replay log, readable source fragment, or another verifiable record must supply the exact text. If verification fails, keep it unresolved.

Do not pass a Short when an obvious direct reply lacks either its readable native box or an explicitly authorized, evidence-backed reconstruction.
