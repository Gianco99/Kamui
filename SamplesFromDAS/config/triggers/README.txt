Trigger Configs
===============
One JSON file per trigger channel. A channel is the set of HLT paths that define a way of selecting events.

Fields
------
  paths      The HLT path names, with a trailing _v* so any version matches
  process    The process name the trigger bits were written under (normally HLT)
  mode       "any" for an OR, "all" for an AND
  vetoes     Optional. Events the channel excludes, each a path list plus the offline requirement that must also hold. Recorded for reference - the job applies neither. Should be implemented later.

Using One
---------
A trigger config does nothing on its own. A content preset points at it, and the job then keeps only events that fired the channel:

  "skim": {"triggers": "run2Lepton"}

Run ./kamui content dvRun2Lepton to see the paths a preset ends up with.

What Is Here Now
----------------
  run2Displaced   Run 2 b-jet and displaced-dijet paths - the displacement-triggered channel
  run2Lepton      Run 2 single-electron and single-muon paths - the lepton-triggered channel
