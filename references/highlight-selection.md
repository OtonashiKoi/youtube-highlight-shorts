# Highlight selection and interchange format

## Selection rubric

Score candidates on payoff, clarity without outside context, emotion/energy, novelty, and visual usefulness. Prefer a varied narrative arc over many repetitions of the same joke or event. For gameplay, consider victories, failures, reactions, discoveries, reversals, and concise reflections. For chat streams, consider announcements, strong opinions, stories, jokes, and audience-response peaks.

Use transcript semantics first. Audio peaks, chat density, scene changes, silence boundaries, and game-state signals may support selection but must not determine it alone. Avoid cutting mid-sentence. Mark uncertain transcript content instead of guessing.

## `highlights.json`

Use UTF-8 JSON:

```json
{
  "source_url": "https://www.youtube.com/watch?v=example",
  "title": "Video title",
  "highlights": [
    {
      "index": 1,
      "start": "00:04:55.000",
      "end": "00:06:30.000",
      "title": "Short readable title",
      "summary": "What happens and why it is worth keeping"
    }
  ]
}
```

Rules:

- Sort by `index`; indices must be unique positive integers.
- Require `end > start` and keep all times within source duration.
- Use `HH:MM:SS.mmm` timestamps.
- Keep titles filesystem-safe: exclude `< > : \ / | ? *` and trailing periods/spaces.
- Aim for 5–16 highlights unless the user specifies otherwise.
- Default total selected duration to roughly 10–25% of a long source, but prioritize quality over quota.
