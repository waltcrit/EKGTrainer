"""
Deep learning model hooks for beat-level and rhythm-level classification.

Models are optional — the pipeline degrades gracefully to classical features
if PyTorch is not installed.

Available
---------
beat_model.py   : BeatCNN — 1-D CNN for per-beat classification
rhythm_model.py : RhythmCNN, RhythmRNN, RhythmTransformer — strip-level models
"""
