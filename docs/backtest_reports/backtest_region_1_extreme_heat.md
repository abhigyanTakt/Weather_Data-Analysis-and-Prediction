# Regional Climatology Alert Backtest Report
**Region ID**: 1  
**Hazard Evaluated**: Extreme Heat  
**Evaluation Window**: 2021-09-28 to 2026-09-26 (5 Years)  

### Verification Metrics
- **Total Observed Extreme Events**: 92
- **Hit Rate (Probability of Detection)**: 19.6% (18/92)
- **False Alarm Rate (FAR)**: 83.3% (90/108)
- **Critical Success Index (CSI)**: 0.099
- **Mean Advance Lead Time**: 48.0 hours

### Threshold Calibration Recommendations
To minimize false alarms while guaranteeing coverage of high-impact events:
- Set Alert Watch at local 95th percentile.
- Elevate to Alert Warning at local 99th percentile or when persistence exceeds 3 consecutive days.
