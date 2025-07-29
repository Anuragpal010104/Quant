import datetime

def generate_risk_report(positions, metrics, compliance_thresholds=None, recent_hedges=None):
    """
    Generate a regulatory risk report string.
    positions: list of position dicts
    metrics: dict with greeks, VaR, etc.
    compliance_thresholds: dict of limits (optional)
    recent_hedges: list of recent hedge dicts (optional)
    """
    notional = sum(abs(p.get('size', 0)) * p.get('S', 0) for p in positions)
    report = [
        f"\U0001F4C8 <b>Regulatory Risk Report</b> ({datetime.datetime.utcnow().isoformat()} UTC)",
        f"Notional Exposure: <b>${notional:,.2f}</b>",
        f"Delta: <b>{metrics.get('delta', 0):.4f}</b>",
        f"Gamma: <b>{metrics.get('gamma', 0):.4f}</b>",
        f"Vega: <b>{metrics.get('vega', 0):.4f}</b>",
        f"Theta: <b>{metrics.get('theta', 0):.4f}</b>",
        f"VaR: <b>{metrics.get('var', 0):,.2f}</b>",
    ]
    # Compliance warnings
    warnings = []
    if compliance_thresholds:
        for k, v in compliance_thresholds.items():
            if abs(metrics.get(k, 0)) > v:
                warnings.append(f"⚠️ {k.upper()} exceeds threshold ({metrics.get(k, 0):.2f} > {v})")
    if warnings:
        report.append("<b>Compliance Warnings:</b>")
        report.extend(warnings)
    # Recent hedge actions
    if recent_hedges:
        report.append("<b>Recent Hedge Actions:</b>")
        for h in recent_hedges[-5:]:
            report.append(f"{h['timestamp']}: {h['side']} {h['size']} {h['asset']} @ {h['price']}")
    return "\n".join(report)

def save_risk_report_to_file(report: str, filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
