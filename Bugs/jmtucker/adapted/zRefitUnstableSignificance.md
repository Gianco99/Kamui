# Rounding alone can push the zRefit significance across `maxShiftSigma`, because its denominator is the difference of two nearly equal variances.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1454`. `distz_sig = distz/sqrt(mag(vnm1.covariance(2,2) - v[0]->covariance(2,2)))`, where one-argument `mag` is `fabs`. When dropping a track barely changes the z variance, rounding in either fit swings that difference, and the significance with it.
- **Kamui:** `vertexing/plugins/DVProducer.cc:398`. Reproduced on purpose to match JMTucker.
- **Impact:** Minor: a decision flips only for a vertex right at the cut. Changing the CMSSW release flipped 4 of 39,005 ZH 2017 DVs and caused about 61 one-track differences in displacement-channel 2017 MC.
- **Fix:** Put a floor under the denominator, or test the dropped track's z distance to the n-1 vertex against that track's own z uncertainty, and retune `maxShiftSigma` afterward. A floor changes the outcome of the 13 to 15% of zRefit track drops in signal MC whose denominator is near zero, far more than the instability flips, so it needs its own signal-efficiency study.
