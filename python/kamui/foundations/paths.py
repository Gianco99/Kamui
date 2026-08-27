"""
Filesystem locations used across kamui.
"""

# Import Block

## Standard Python imports
import os

## Repository root, worked out from this file's own location
PKG_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../Kamui/python/kamui
REPO_DIR = os.path.dirname(os.path.dirname(PKG_DIR))                     # .../Kamui

## Stage directories
PRODUCTION_DIR = os.path.join(REPO_DIR, "ntupleProduction")
SELECTION_DIR  = os.path.join(REPO_DIR, "ntupleSelection")

## Config files, the whole user interface
CONFIG_DIR   = os.path.join(REPO_DIR, "config")
SAMPLES_DIR  = os.path.join(CONFIG_DIR, "samples")
CONTENT_DIR  = os.path.join(CONFIG_DIR, "content")
TRIGGERS_DIR = os.path.join(CONFIG_DIR, "triggers")
SITES_FILE   = os.path.join(CONFIG_DIR, "sites.json")
SELECTIONS_DIR = os.path.join(CONFIG_DIR, "selections")
XSEC_DIR       = os.path.join(CONFIG_DIR, "crossSections")
LUMI_FILE      = os.path.join(CONFIG_DIR, "lumi.json")

## Everything else we need for job submission and querying DAS
CMSSW_DIR    = os.path.join(PRODUCTION_DIR, "cmssw")       # cmsRun cfg and table builder
JOBS_DIR     = os.path.join(PRODUCTION_DIR, "jobs")        # generated job areas (gitignored)
CACHE_DIR    = os.path.join(PRODUCTION_DIR, ".dasCache")   # dasgoclient response cache
