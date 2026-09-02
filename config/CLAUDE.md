# Config

- Keys beginning with `_` are stripped at every depth, so a `_doc` nested inside a block is dropped like any other.
- `loadWithIncludes` flattens `include` depth-first and deep-merges. A circular include raises.
- Only dicts merge. Lists and scalars replace wholesale, so a child that names a list throws away the parent's entirely.
- A name resolves against the search directory, then one level of subdirectories beneath it in sorted order.
- Nothing outside `configReaders/` may open these files. `./kamui check` enforces it by scanning `python/kamui/` outside `configReaders/`
  - `select/normalization.py` is an exception.
- CRAB refuses an `outLFNDirBase` under another user's `/store/user` area, so it cannot write to the shared `lpcdisplacedvertices` directory and gets its own `crabStageoutBase`.
- Condor stages out with `xrdcp` and has no such restriction, so it keeps the group area.
