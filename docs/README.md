# docs

Planning documents and reference notes. A document here is transient: it exists while the study it describes is live, and moves to `legacy/` when that study is finished, so the reasoning behind a past decision stays recoverable. [legacy/README.md](legacy/README.md) gives the archiving convention.

Two kinds of thing belong here. A **plan** is what we intend to do and why, written before the work. A **reference note** is a measurement or a table that code needs but should not hardcode, such as the jet identification working points in `JetID.txt`.

Measurements belong here. A number measured from one sample goes stale the next time somebody edits the code that produced it, and a reader of a CLAUDE.md has no way to tell how old it is. Here a document is dated and understood to be a snapshot.

These stay plain `.txt`, without Markdown syntax, since they are read in a terminal as often as on GitHub. Markdown is used in the `README.md` files elsewhere in the repo.
