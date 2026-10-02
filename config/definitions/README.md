# Definition Documentation

A definition is a named list of cuts that you write once and reuse by name. For example, `analysisJet` holds the cuts a jet must pass to count in the analysis. Anywhere you need those cuts, you write `{"definition": "analysisJet"}` in their place, so changing the file changes every cut that names it.

- Each file here holds one definition, named after the file. Its `requirements` is a list of cuts in the same syntax as a selection's object cut, or an object keyed by era when the cuts differ by era.
- You can name a definition inside any requirement list: in a selection's object cut or count, in another definition, or in the `VertexJet` collection.
- Kamui replaces each name with its cuts when it reads the configs, so jobs never read this folder.
- Definitions sit in a folder per run, `run2/` or `run3/`, since IDs and working points differ between runs. A config reads the definition of that name from its era's run folder.

The shape of a definition file, and a selection cut that uses one:

```text
{"requirements": [{"variable": "<variable>", "above": <value>}, {"definition": "<another definition>"}]}
{"name": "<cut>", "type": "object", "collection": "<collection>", "min": 1, "requirements": [{"definition": "<definition>"}]}
```

| File | Defines |
|---|---|
| `tightLepVeto.json` | The TightLepVeto PF jet ID, with one list per era |
| `analysisJet.json` | The jets the analysis counts, built on `tightLepVeto` |
| `deepJetLoose.json` | DeepJet loose b-tag working point, per era |
| `plateauMuon.json` | A muon on the plateau of the single-muon trigger, with ID, isolation and impact parameters |
| `plateauElectron.json` | An electron on the plateau of the single-electron trigger, with ID and impact parameters |

See `config/selections/README.md` for the full cut syntax.

## Caveats

- `tightLepVeto` uses `above` and `below`, the exclusive bounds. Its `chHEF` cut has to reject the jets with no charged energy at all. Those jets sit exactly on its threshold, so an inclusive `min` would keep them.
