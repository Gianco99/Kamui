"""
Filesystem locations used across kamui.
"""

# Import Block

## Standard Python imports
import os

## Repository root, worked out from this file's own location
PKG_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../Kamui/python/kamui
REPO_DIR = os.path.dirname(os.path.dirname(PKG_DIR))                     # .../Kamui

## Sample processing
SAMPLES_DIR_STAGE = os.path.join(REPO_DIR, "SamplesFromDAS")

## Config files, the whole user interface
CONFIG_DIR   = os.path.join(SAMPLES_DIR_STAGE, "config")
SAMPLES_DIR  = os.path.join(CONFIG_DIR, "samples")
CONTENT_DIR  = os.path.join(CONFIG_DIR, "content")
TRIGGERS_DIR = os.path.join(CONFIG_DIR, "triggers")
SITES_FILE   = os.path.join(CONFIG_DIR, "sites.json")

## Everything else we need for job submission and querying DAS
CMSSW_DIR    = os.path.join(SAMPLES_DIR_STAGE, "cmssw")       # cmsRun cfg and table builder
JOBS_DIR     = os.path.join(SAMPLES_DIR_STAGE, "jobs")        # generated job areas (gitignored)
CACHE_DIR    = os.path.join(SAMPLES_DIR_STAGE, ".dasCache")   # dasgoclient response cache
