"""
Arrhythmia detection and classification pipeline.

Modules
-------
constants   : canonical arrhythmia classes, display names, colors, explanations
ingest      : load WFDB records
preprocess  : filtering, baseline wander removal, resampling
rpeaks      : R-peak detection, RR interval computation
segments    : beat windows and rhythm strip windows
features    : classical + wavelet/frequency feature extraction
inference   : end-to-end orchestration
scoring     : PhysioNet-compatible evaluation metrics
models/     : deep-learning hooks (beat_model, rhythm_model)
"""
