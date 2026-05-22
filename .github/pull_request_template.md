## 🏗️ Colossus Phase PR

### Phase
- [ ] Phase 0 — Geotechnical
- [ ] Phase 1 — Foundation
- [ ] Phase 2 — Water Management
- [ ] Phase 3 — Architecture/Security
- [ ] Phase 4 — GPU Cluster
- [ ] Phase 5 — Cooling
- [ ] Phase 6 — Power
- [ ] Phase 7 — Digital Twin
- [ ] Phase 8 — Commissioning

### Change Type
- [ ] New connector/agent
- [ ] KPI update
- [ ] Bug fix
- [ ] Documentation
- [ ] Security patch

### Summary
<!-- What was built/changed and why -->

### KPIs Impacted
<!-- List any KPIs this change affects with expected delta -->

### Testing
- [ ] Unit tests passing
- [ ] Dry-run `python main.py --dry-run` passes
- [ ] No secrets committed (secret scan passed)
- [ ] InfluxDB measurements validated
- [ ] Kafka topic schema verified

### APEX Integration
- [ ] `APEX_MANIFEST.json` updated
- [ ] Connector registered in `apex-connector-registry`
- [ ] `colossus-gateway` notified

### Checklist
- [ ] Code reviewed for TEMPEST/security compliance
- [ ] No hardcoded credentials
- [ ] Logging uses structured format
- [ ] Async patterns correct (no blocking calls in coroutines)
