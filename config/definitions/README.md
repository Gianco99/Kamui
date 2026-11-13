# Definitions

A definition is a named list of cuts that you write once and reuse by name. For example, `analysisJet` holds the cuts a jet must pass to count in the analysis. Anywhere you need those cuts, you write `{"definition": "analysisJet"}` in their place, so changing the file changes every cut that names it.

- Each file here holds one definition, named after the file. Its `requirements` is a list of cuts in the same syntax as a selection's object cut, or an object keyed by era when the cuts differ by era.
- You can name a definition inside any requirement list: in a selection's object cut or count, in another definition, or in the `VertexJet` collection.
- Definitions sit in two folders, `run2/` and `run3/`, since IDs and working points differ between runs. A config reads the definition of that name from its era's run folder, so a Run 3 config can only name a definition in `run3/`.

The shape of a definition file, and a selection cut that uses one:

```text
{"requirements": [{"variable": "<variable>", "above": <value>}, {"definition": "<another definition>"}]}
{"name": "<cut>", "type": "object", "collection": "<collection>", "min": 1, "requirements": [{"definition": "<definition>"}]}
```

| File in `run2/` | Defines |
|---|---|
| `tightLepVeto.json` | The TightLepVeto PF jet ID, with one list per era |
| `analysisJet.json` | The jets the analysis counts, built on `tightLepVeto` |
| `deepJetLoose.json` | DeepJet loose b-tag working point, per era |
| `deepJetTight.json` | DeepJet tight b-tag working point, per era |
| `plateauMuon.json` | A muon on the plateau of the single-muon trigger, with ID, isolation and impact parameters |
| `plateauElectron.json` | An electron on the plateau of the single-electron trigger, with ID and impact parameters |
| `tightDV.json` | A high-quality DV that enters our analysis selection |

See `config/selections/README.md` for the full cut syntax.

## Caveats

- Jets with no charged energy sit exactly on the `chHEF` threshold of `tightLepVeto`, so that cut must use the exclusive `above` to reject them.
