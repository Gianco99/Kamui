"""
Slimmed-MiniAOD output: which EDM collections survive.

The flat tree is the analysis format, but it is a fixed set of quantities - if
something turns out to be missing you have to go back to the grid. A slimmed
MiniAOD alongside it keeps the full CMSSW objects, so re-vertexing or adding a
variable later is a local reprocessing rather than a re-download.

Groups are named after physics, not after EDM type names, for the same reason
content configs are: nobody should have to know that vector<pat::Jet> is spelled
"patJets" in an outputCommands string. Keeps are written label-first
("keep *_slimmedJets_*_*") because that form is robust - getting a friendly class
name slightly wrong silently keeps nothing.
"""

GROUPS = {
    # Always included; the file is not usable without these.
    "core": [
        "keep edmTriggerResults_*_*_*",
        "keep *_patTrigger_*_*",
        "keep *_offlineBeamSpot_*_*",
        "keep *_offlineSlimmedPrimaryVertices_*_*",
        "keep *_fixedGridRhoFastjetAll_*_*",
        "keep *_fixedGridRhoFastjetCentral_*_*",
        "keep *_fixedGridRhoAll_*_*",
        "keep *_bunchSpacingProducer_*_*",
    ],
    "triggerObjects": [
        "keep *_slimmedPatTrigger_*_*",
    ],
    "jets": [
        "keep *_slimmedJets_*_*",
        "keep *_slimmedJetsPuppi_*_*",
        # tagInfos are per-jet track/vertex detail and dominate the jet size.
        "drop *_slimmedJets_tagInfos_*",
        "drop *_slimmedJetsPuppi_tagInfos_*",
    ],
    "fatJets": [
        "keep *_slimmedJetsAK8_*_*",
        "keep *_slimmedJetsAK8PFPuppiSoftDropPacked_*_*",
    ],
    "caloJets": [
        "keep *_slimmedCaloJets_*_*",
    ],
    "leptons": [
        "keep *_slimmedMuons_*_*",
        "keep *_slimmedElectrons_*_*",
    ],
    "displacedLeptons": [
        # Run 3 MiniAOD only. Harmless on Run 2 - a keep that matches nothing.
        "keep *_slimmedDisplacedMuons_*_*",
        "keep *_displacedStandAloneMuons_*_*",
        "keep *_displacedGlobalMuons_*_*",
    ],
    "photons": [
        "keep *_slimmedPhotons_*_*",
    ],
    "taus": [
        "keep *_slimmedTaus_*_*",
    ],
    "met": [
        "keep *_slimmedMETs_*_*",
        "keep *_slimmedMETsPuppi_*_*",
    ],
    "tracks": [
        "keep *_packedPFCandidates_*_*",
        "keep *_lostTracks_*_*",
    ],
    "displacedTracks": [
        # reco::Track, with full track parameters rather than packed ones.
        # Present in Run 3 MiniAOD; absent in Run 2 UL, where this keeps nothing.
        "keep *_displacedTracks_*_*",
    ],
    "vertices": [
        "keep *_slimmedSecondaryVertices_*_*",
        "keep *_slimmedKshortVertices_*_*",
        "keep *_slimmedLambdaVertices_*_*",
    ],
    "gen": [
        "keep *_prunedGenParticles_*_*",
        "keep *_packedGenParticles_*_*",
        "keep *_slimmedGenJets_*_*",
        "keep *_generator_*_*",
        "keep *_externalLHEProducer_*_*",
        "keep *_slimmedAddPileupInfo_*_*",
        "keep *_genMetTrue_*_*",
    ],
    "egammaExtras": [
        # Needed if electron IDs are to be recomputed downstream. Large.
        "keep *_reducedEgamma_*_*",
    ],
    "scouting": [
        "keep *_hltScouting*_*_*",
    ],
}

# Groups that are gen-level and get dropped automatically when running on data.
MC_ONLY_GROUPS = {"gen"}


def buildOutputCommands(cfg, isMC=True):
    """
    cfg: the "miniaod" block of a content config:
        {"keep": ["jets", "tracks", ...], "keepExtra": [...raw commands...], "drop": [...]}
    Returns a list of outputCommands strings, starting with "drop *".
    """
    if not cfg:
        return []
    wanted = list(cfg.get("keep", []))
    unknown = [g for g in wanted if g not in GROUPS]
    if unknown:
        raise ValueError(
            f"unknown miniaod keep group(s): {unknown}. Known groups: {', '.join(sorted(GROUPS))}"
        )

    commands = ["drop *"]
    seen = set()
    for g in ["core"] + wanted:
        if g in MC_ONLY_GROUPS and not isMC:
            continue
        for c in GROUPS[g]:
            if c not in seen:
                seen.add(c)
                commands.append(c)

    commands += list(cfg.get("keepExtra", []))
    commands += [c if c.startswith("drop ") else f"drop {c}" for c in cfg.get("drop", [])]
    return commands
