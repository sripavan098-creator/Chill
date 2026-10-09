## Summary

<!-- What does this change and why? One or two sentences. -->

## Milestone

<!-- e.g. v0.5 — stronger voice auth. -->

## Privacy and security checklist

- [ ] Raw audio is never persisted or uploaded; temporary recordings are deleted after processing.
- [ ] No secrets, tokens or keys are committed.
- [ ] Voice is never the only factor for a sensitive action; a fallback stays available.
- [ ] No background listening or silent recording was added.

## Testing

<!-- Commands run and their result. -->

- [ ] `apps/mobile`: `npm run typecheck`, `npm run lint`, `npm test`
- [ ] `services/api`: `ruff check app tests`, `pytest -q`
- [ ] `docs/TASKS.md` updated if a milestone item changed

## Notes

<!-- Anything reviewers should know: trade-offs, follow-ups, risks. -->
