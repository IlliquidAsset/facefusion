#!/usr/bin/env python3
"""
Factory Telemetry Dashboard
Real-time monitoring for autonomous quality iteration loop
"""

import json
import os
from datetime import datetime
from pathlib import Path

def read_iteration_log():
    """Read iteration log and return list of iterations."""
    log_path = Path("factory/iteration_log.jsonl")
    if not log_path.exists():
        return []
    
    iterations = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    iterations.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return iterations

def generate_html():
    """Generate HTML dashboard."""
    iterations = read_iteration_log()
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Factory Quality Iteration Loop - Telemetry</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: -apple-system, sans-serif; margin: 40px; background: #1a1a1a; color: #e0e0e0; }
        h1 { color: #4fc3f7; }
        .metric { background: #2d2d2d; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .metric-label { color: #888; font-size: 12px; }
        .metric-value { font-size: 24px; font-weight: bold; }
        .pass { color: #4caf50; }
        .fail { color: #f44336; }
        .pending { color: #ff9800; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; color: #4fc3f7; }
        tr:hover { background: #2a2a2a; }
        .iteration-card { background: #252525; padding: 20px; margin: 15px 0; border-radius: 10px; border-left: 4px solid #4fc3f7; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .status-running { background: #ff9800; color: #000; }
        .status-passed { background: #4caf50; color: #000; }
        .status-failed { background: #f44336; color: #fff; }
        .status-plateau { background: #9c27b0; color: #fff; }
        .images-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px; }
        .images-grid img { width: 100%; border-radius: 4px; }
        .refresh-time { color: #666; font-size: 11px; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>🔬 Factory Quality Iteration Loop</h1>
    <div class="refresh-time">Last updated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """ (auto-refreshes every 30s)</div>
    
    <div class="metric">
        <div class="metric-label">Total Iterations</div>
        <div class="metric-value">""" + str(len(iterations)) + """</div>
    </div>
"""
    
    if iterations:
        latest = iterations[-1]
        identity_sim = latest.get('metrics_summary', {}).get('identity_similarity', 0)
        cost = latest.get('cost_so_far', 0)
        status = latest.get('status', 'unknown')
        
        html += f"""
    <div class="metric">
        <div class="metric-label">Latest Identity Similarity</div>
        <div class="metric-value {'pass' if identity_sim >= 0.65 else 'fail'}">{identity_sim:.4f} / 0.65 target</div>
    </div>
    
    <div class="metric">
        <div class="metric-label">RunPod Cost</div>
        <div class="metric-value">${cost:.2f} / $10.00 budget</div>
    </div>
    
    <div class="metric">
        <div class="metric-label">Current Status</div>
        <div class="metric-value">
            <span class="status-badge status-{status}">{status.upper()}</span>
        </div>
    </div>
"""
        
        html += """
    <h2>📊 Iteration History</h2>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Time</th>
                <th>Identity Score</th>
                <th>Status</th>
                <th>Cost</th>
                <th>Commit</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for i, it in enumerate(reversed(iterations[-20:]), 1):  # Show last 20
            num = it.get('iteration_number', 0)
            ts = it.get('timestamp', 'N/A')
            metrics = it.get('metrics_summary', {})
            identity = metrics.get('identity_similarity', 0)
            stat = it.get('status', 'unknown')
            cost_it = it.get('cost_so_far', 0)
            commit = it.get('git_commit_hash', 'N/A')[:8]
            
            html += f"""
            <tr>
                <td>{num}</td>
                <td>{ts}</td>
                <td class="{'pass' if identity >= 0.65 else 'fail'}">{identity:.4f}</td>
                <td><span class="status-badge status-{stat}">{stat}</span></td>
                <td>${cost_it:.2f}</td>
                <td><code>{commit}</code></td>
            </tr>
"""
        
        html += """
        </tbody>
    </table>
"""
        
        # Show detailed view of latest iteration
        html += """
    <h2>🔍 Latest Iteration Details</h2>
"""
        html += f"""
    <div class="iteration-card">
        <h3>Iteration {latest.get('iteration_number', 0)} - {latest.get('status', 'unknown').upper()}</h3>
        <p><strong>Changes Made:</strong> {latest.get('changes_made', 'N/A')}</p>
        <p><strong>Diagnosis:</strong> {latest.get('diagnosis', {}).get('summary', 'N/A')}</p>
        <p><strong>Git Commit:</strong> <code>{latest.get('git_commit_hash', 'N/A')}</code></p>
    </div>
"""
    else:
        html += """
    <div class="metric">
        <div class="metric-label">Status</div>
        <div class="metric-value pending">Waiting for first iteration...</div>
    </div>
    
    <div class="iteration-card">
        <h3>🚀 Getting Started</h3>
        <p>The iteration loop hasn't started yet. Tasks are running in parallel:</p>
        <ul>
            <li>Task 1: Clone REFace + validate on RunPod A40</li>
            <li>Task 2: Set up RunPod SSH bridge</li>
        </ul>
        <p>Once these complete, Task 3 (wire orchestrator) and Task 4 (SSH execution) will begin.</p>
    </div>
"""
    
    html += """
    <h2>🖼️ Judge Images</h2>
    <p>Images sent to LLM judge for perceptual evaluation:</p>
"""
    
    # Show recent judge images
    judge_dir = Path("factory/judge_images")
    if judge_dir.exists():
        recent_dirs = sorted(judge_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
        for d in recent_dirs:
            if d.is_dir():
                html += f"""
    <div class="iteration-card">
        <h4>{d.name}</h4>
        <div class="images-grid">
"""
                for img in sorted(d.glob("*.png"))[:6]:
                    html += f'<img src="{img}" alt="{img.name}">\n'
                html += """
        </div>
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    return html

def main():
    """Generate and save telemetry dashboard."""
    html = generate_html()
    output_path = Path("factory/telemetry.html")
    output_path.write_text(html)
    print(f"Telemetry dashboard updated: {output_path.absolute()}")
    print(f"Open with: open {output_path}")

if __name__ == "__main__":
    main()
