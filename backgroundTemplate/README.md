# Background Template

This folder builds the 2V background template, the predicted shape of the background in events with two DVs. It is made from 1V events, events with exactly one DV. Each 1V DV that passes the template's cuts goes into a pool, split into categories by b tagging and number of PVs so that paired DVs come from similar events. Each DV is paired with a random DV of its category, the tracks of the two are refit together with the ported JMTucker vertexer, and the pair fills the template at the sum of the two input dBVs when the refit gives back two DVs with the requested track counts. The limits use `h_c1v_sumdbv_revertexed_w_errorbars`, rebinned to the analysis bins.

The code reproduces the outputs of Alec's `2v_from_jets.cc` byte for byte, known bugs included. Each kept bug is marked "Kept for the bit-identical check" in the code, with its file in `Bugs/backgroundTemplate/` or `Bugs/jmtucker/adapted/`.

It builds against CMSSW_10_6_48 and reads JMTucker MiniTrees, so it runs in the el7 container on its own, outside the `kamui` CLI. From this folder:

```
/cvmfs/cms.cern.ch/common/cmssw-el7 -B /uscms_data -- bash build.sh
/cvmfs/cms.cern.ch/common/cmssw-el7 -B /uscms_data -- bash run.sh outputs/<name> --channel lepton
```

`run.sh` passes every option after the output folder to `2v_from_jets.exe`. With only `--channel`, it runs the channel's production set. `--help` prints the options: year, track counts, b-tag selection and MC.

## Files

| File | What it does |
|---|---|
| `2v_from_jets.cc` | The template code |
| `Makefile`, `build.sh` | Build `2v_from_jets.exe` in the el7 container, logging to `build.log` |
| `run.sh` | Runs `2v_from_jets.exe` in the el7 container, logging to `<outDir>/run.log` |
| `2v_from_jets_new.py` | Alec's MC weight helper, which `2v_from_jets.exe` calls from its own folder in `--mc` runs |
| `include/` | Copies of JMTucker's `MiniNtuple.h`, `MiniNtuple.cc` and `VertexAux.h` from Alec's checkout, which the build uses ahead of the CMSSW area's own |
| `validation/` | Scripts that check the outputs against Alec's |

## Validation

- `validation/runAll.sh` runs every validated configuration into `outputs/final`, two containers at a time.
- `validation/validateAll.sh` compares each output with its reference: every histogram (`compareOutputs.py`), the stored bytes of every object (`compareRaw.py`) and `cb_vals.csv`. It needs python3 with uproot, so run it in the Kamui environment, outside the container.
- `validation/cliChecks.sh` runs the command-line checks and prints each command's exit code and first message.
- `validation/makeExtraReferences.py` writes copies of Alec's code with `main()` edited for the configurations it never ran, and `validation/runExtra.sh` runs those copies next to the template code.

```
bash validation/runAll.sh
bash validation/validateAll.sh
```

## Where the Outputs Live

Binaries, logs and ROOT outputs stay out of the repo. Everything the validation compares against is under `/uscms/home/gdecastr/nobackup/work/BackgroundTemplateRebuild`:

- `alecSnapshot_2026-11-05_1640/`: Alec's source as of 2026-11-05 16:40, with his helper, Makefile, downstream macros, his outputs in `alecOutputs/` and `SHA256SUMS`.
- `reference/` and `referenceBveto/`: Alec's code with only its input paths and a blinding guard changed, set to the lepton and the displacement channel, with the production outputs each wrote.
- `rewrite/referenceMC/`, `rewrite/referenceSidebands/` and `rewrite/referenceExtra/`: the MC, sideband and extra references.
- `rewrite/outputs/final/`: the template outputs that `validateAll.sh` last passed, with its record in `rewrite/validation/validateAll.out`.
- `stopperFindings.md` and `variants/`: the measurements behind the bug files.

## Caveats

- Fixing a kept bug changes the template, so treat it as a physics change: rerun the production set and compare the bins before and after.
- In data, the code skips every event with two DVs of 5 or more tracks before filling anything, which keeps the signal region blind. Still never open `h_2v_*` or `c_sumdbv*` in a data output. The comparison scripts skip them for that reason.
- Displacement-channel runs need a lot of memory. Run at most two at a time, as `runAll.sh` does.
- `build.sh`, `run.sh` and `cliChecks.sh` use Gianfranco's CMSSW_10_6_48 area unless `CMSSW_SRC` points at another one.
- The input MiniTrees are Joey's, read in place from `/uscms_data/d3/joeyr/crabdirs/`. Never write there.
- `validateAll.sh`, `runExtra.sh` and `makeExtraReferences.py` find the references by absolute path. If `BackgroundTemplateRebuild` moves, update the paths at the top of each.
