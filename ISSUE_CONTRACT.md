# Issue Contract — `xai-colossus-cooling`

## Pain
Facility IT load exceeds coolant heat rejection → throttle/critical without first-principles check.

## Claim
Q=mcpΔT assessor returns NOMINAL/THROTTLE_RISK/CRITICAL with real SI math.

## Proof
```bash
python3 job-app/helix/proofs/proof_thermal.py
```

## Done when
Proof exits 0. Architecture (strand/integrity/helix) is **not** a substitute for this proof.

## Anti-claim
Not claiming live Colossus plant control.
