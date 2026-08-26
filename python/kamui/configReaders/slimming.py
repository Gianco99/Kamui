"""
Turns the physics names in a preset's miniaod block into the EDM outputCommands that write a slimmed MiniAOD.
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
