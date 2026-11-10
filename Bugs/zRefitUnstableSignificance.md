# The zRefit significance divides the z shift by the square root of the difference of two nearly equal z variances, so a tiny numerical difference in the fits can move it across maxShiftSigma.

- **JMTucker:** `MFVNeutralino/plugins/Vertexer.cc:1454`. `distz_sig = distz/sqrt(mag(vnm1.covariance(2,2) - v[0]->covariance(2,2)))`, where one-argument `mag` is `fabs`. When dropping a track barely changes the z variance, the denominator is the small difference of two nearly equal numbers, so rounding in either fit swings the significance.
- **Kamui:** `vertexing/plugins/DVProducer.cc:377`. Reproduced on purpose to match JMTucker.
- **Fix:** Put a floor under the denominator, or test the dropped track's z distance to the n-1 vertex against that track's own z uncertainty, and retune maxShiftSigma afterward.
