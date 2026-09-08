# Tools

- Neither script is imported by kamui or runs as part of a job, and both need `cmsenv`.
- `triggerYields.py`
    - The denominator is already skimmed. Both presets it accepts declare `skim.triggers`, so every event in the file passed the channel OR and `eff` lands at essentially 100%. The number is a consistency check that the stored bits agree with the skim the job applied. `--perPath` is the informative output: it shows which paths carry the channel and which are absent from the era's menu.
    - `mode` is ignored. `yieldsFor` always joins paths with `||`, so a config saying `mode: "all"` is silently ORed.
    - It re-resolves the channel from today's configs rather than from the `resolvedContent` already in `task.json`, so editing a preset after a task ran changes what this reports.
    - `listEos` reads the flat layout condor writes. A CRAB task records `outLFNDirBase` but nests its output below that level, so nothing is found. Use `--files` there.
- `inspectMiniAOD.py`
    - A collection is reported from the first event that has it. A signal sample can easily have no electrons in event 1, so reporting only event 1 would read as "these IDs are not embedded".
