# `requirements` and `jec` work only on a `vertexJet` collection.

- **Where:** `python/kamui/configReaders/content.py:225-228` rejects both keys on every other kind. Those collections choose their objects with a CMSSW `cut` string (292).
- **Problem:** Collections pick objects with two grammars: `requirements`, with definitions and era-keyed thresholds, on `vertexJet`, and a raw cut string everywhere else.
- **Decision needed:** Make `requirements` the cut grammar for every collection.
