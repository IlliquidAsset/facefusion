#!/usr/bin/env python3
"""
Factory Telemetry Dashboard
Real-time monitoring for autonomous quality iteration loop
"""

import base64
import json
import os
from datetime import datetime
from pathlib import Path


def read_iteration_log():
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


def _read_live_status() -> dict:
    """Read live status from local cache (synced from RunPod)."""
    status_path = Path("factory/results/live_status.json")
    if not status_path.exists():
        return {}
    try:
        with open(status_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _sync_live_status():
    """Pull live_status.json from RunPod to local cache."""
    import subprocess
    try:
        subprocess.run(
            [
                "scp", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                "-i", os.path.expanduser("~/.ssh/id_ed25519"), "-P", "22029",
                "root@194.68.245.208:/workspace/watserface/factory/results/live_status.json",
                "factory/results/live_status.json",
            ],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass


def _sync_videos():
    """Pull video outputs from RunPod to local cache (only if newer)."""
    import subprocess
    video_names = [
        "video_swap_batched_h264.mp4",
        "video_swap_softmask_h264.mp4",
    ]
    for name in video_names:
        local_path = Path(f"factory/results/{name}")
        remote_path = f"root@194.68.245.208:/workspace/watserface/factory/results/{name}"
        try:
            subprocess.run(
                [
                    "scp", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                    "-i", os.path.expanduser("~/.ssh/id_ed25519"), "-P", "22029",
                    remote_path, str(local_path),
                ],
                capture_output=True, timeout=30,
            )
        except Exception:
            pass


def _live_status_section() -> str:
    status = _read_live_status()
    if not status:
        return '<div class="metric"><div class="metric-label">Live Status</div><div class="metric-value pending">No active process</div></div>\n'

    phase = status.get("phase", "unknown")
    detail = status.get("detail", "")
    pct = status.get("pct", 0)
    ts = status.get("timestamp", "")
    progress = status.get("progress", 0)
    total = status.get("total", 0)
    extra_info = ""

    is_stale = True
    if status.get("timestamp"):
        try:
            ts_val = datetime.fromisoformat(status["timestamp"])
            is_stale = (datetime.now() - ts_val).total_seconds() > 300
        except (ValueError, TypeError):
            is_stale = True

    pulse_class = ""
    if phase not in ["done", "error"] and not is_stale:
        pulse_class = "pulse-active"

    if status.get("batch_size"):
        extra_info += f' | batch={status["batch_size"]}'
    if status.get("ddim_steps"):
        extra_info += f' | steps={status["ddim_steps"]}'
    if status.get("inference_time"):
        extra_info += f' | inference={status["inference_time"]:.1f}s'
    if status.get("fps_throughput"):
        extra_info += f' | {status["fps_throughput"]:.1f} fps'
    if status.get("total_time"):
        extra_info += f' | total={status["total_time"]:.0f}s'
    if status.get("output_path"):
        extra_info += f' | output={os.path.basename(status["output_path"])}'

    phase_colors = {
        "init": "#ff9800", "extract": "#2196f3", "prepare": "#2196f3",
        "inference": "#ff5722", "compose": "#9c27b0", "assemble": "#4caf50",
        "encode": "#4caf50", "done": "#4caf50", "error": "#f44336",
    }
    color = phase_colors.get(phase, "#888")

    bar_html = ""
    if total > 0 and phase != "done":
        bar_html = f'''
        <div style="background:#444;border-radius:4px;height:24px;margin:8px 0;overflow:hidden;">
            <div style="background:{color};height:100%;width:{pct}%;transition:width 0.3s;display:flex;align-items:center;padding-left:8px;">
                <span style="font-size:11px;color:#000;font-weight:bold;">{pct}%</span>
            </div>
        </div>'''

    done_class = "pass" if phase == "done" else ""

    return f'''
    <div class="iteration-card" style="border-left-color:{color};">
        <h3 style="margin-top:0;">
            <span class="status-badge {pulse_class}" style="background:{color};color:#000;">{phase.upper()}</span>
            Live Status
        </h3>
        <div class="metric-value {done_class}" style="font-size:18px;">{detail}</div>
        {bar_html}
        <div style="color:#666;font-size:11px;margin-top:6px;">{ts}{extra_info}</div>
        <div style="color:#666;font-size:11px;">Progress: {progress}/{total}</div>
    </div>
'''


def _img_to_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _video_to_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:video/mp4;base64,{data}"


def _video_outputs_section() -> str:
    results_dir = Path("factory/results")
    videos = [
        ("video_swap_softmask_h264.mp4", "Soft Mask Composite (latest)"),
        ("video_swap_batched_h264.mp4", "Raw REFace Composite"),
    ]

    found = []
    for fname, label in videos:
        vpath = results_dir / fname
        if vpath.exists():
            size_mb = vpath.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(vpath.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            found.append((vpath, label, size_mb, mtime))

    if not found:
        return ""

    html = '<h2>Video Outputs</h2>\n'
    for vpath, label, size_mb, mtime in found:
        uri = _video_to_data_uri(vpath)
        html += f'''
    <div class="iteration-card">
        <h3 style="margin-top:0;">{label}</h3>
        <div style="color:#666;font-size:11px;margin-bottom:8px;">{vpath.name} &mdash; {size_mb:.1f}MB &mdash; {mtime}</div>
        <video controls loop style="width:100%;border-radius:8px;background:#000;" preload="auto">
            <source src="{uri}" type="video/mp4">
        </video>
    </div>
'''
    return html


def _result_images_section() -> str:
    latest_dir = Path("factory/results/latest")
    comparison = latest_dir / "comparison.png"
    if not comparison.exists():
        return '<p style="color:#666;">No swap results yet. Run a factory scenario to generate images.</p>'

    comp_uri = _img_to_data_uri(comparison)
    source_uri = _img_to_data_uri(latest_dir / "source.png")
    result_uri = _img_to_data_uri(latest_dir / "result.png")

    html = f'<img src="{comp_uri}" alt="Source / Target / Result comparison" style="width:100%;border-radius:8px;margin:10px 0;">\n'

    if source_uri and result_uri:
        html += """
    <details style="margin-top:10px;">
        <summary style="cursor:pointer;color:#4fc3f7;">View full-resolution source &amp; result</summary>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;">
"""
        html += f'<div><p style="color:#888;font-size:12px;">SOURCE</p><img src="{source_uri}" style="width:100%;border-radius:4px;"></div>\n'
        html += f'<div><p style="color:#888;font-size:12px;">RESULT</p><img src="{result_uri}" style="width:100%;border-radius:4px;"></div>\n'
        html += """
        </div>
    </details>
"""
    return html


def _archive_gallery() -> str:
    results_dir = Path("factory/results")
    if not results_dir.exists():
        return ""

    archive_dirs = sorted(
        [d for d in results_dir.iterdir() if d.is_dir() and d.name != "latest"],
        key=lambda x: x.name,
        reverse=True,
    )[:5]

    if not archive_dirs:
        return ""

    html = '<h2>Previous Runs</h2>\n'
    for d in archive_dirs:
        comp = d / "comparison.png"
        if comp.exists():
            uri = _img_to_data_uri(comp)
            html += f"""
    <div class="iteration-card">
        <h4>{d.name}</h4>
        <img src="{uri}" style="width:100%;border-radius:4px;">
    </div>
"""
    return html


def _compute_deltas(iterations):
    """Compare latest vs prior iteration metrics. Returns dict of delta info."""
    if len(iterations) < 2:
        return {}
    
    latest = iterations[-1].get('metrics_summary', {})
    prior = iterations[-2].get('metrics_summary', {})
    latest_cost = iterations[-1].get('cost_so_far', 0)
    prior_cost = iterations[-2].get('cost_so_far', 0)
    
    def _delta(curr, prev, threshold):
        diff = curr - prev
        if abs(diff) < threshold:
            return ('→', 'flat', diff)
        elif diff > 0:
            return ('↑', 'up', diff)
        else:
            return ('↓', 'down', diff)
    
    return {
        'identity': _delta(latest.get('identity_similarity', 0), prior.get('identity_similarity', 0), 0.01),
        'ssim': _delta(latest.get('ssim', 0), prior.get('ssim', 0), 0.005),
        'cost': _delta(latest_cost, prior_cost, 0.01),
    }


def _iteration_timeline_section(iterations):
    """Render a horizontal timeline of iteration markers."""
    if len(iterations) < 2:
        return ""
    
    # Cap at last 15 iterations for readability
    display_iterations = iterations[-15:]
    
    status_colors = {
        'failed': '#f44336',
        'passed': '#4caf50',
        'running': '#ff9800',
        'plateau': '#9c27b0',
    }
    
    markers_html = ""
    for i, it in enumerate(display_iterations):
        num = it.get('iteration_number', i)
        status = it.get('status', 'unknown')
        color = status_colors.get(status, '#888')
        identity = it.get('metrics_summary', {}).get('identity_similarity', 0)
        is_latest = (i == len(display_iterations) - 1)
        
        dot_class = "timeline-dot-latest" if is_latest else "timeline-dot"
        markers_html += f'''
            <div class="timeline-marker">
                <div class="{dot_class}" style="background:{color};" title="Iteration {num}: identity={identity:.4f} ({status})"></div>
                <span class="timeline-label">#{num}</span>
            </div>'''
    
    return f'''
    <div class="iteration-timeline">
        <div class="timeline-title">Iteration Progress</div>
        <div class="timeline-track">
            {markers_html}
        </div>
    </div>
'''


def generate_html():
    iterations = read_iteration_log()

    status = _read_live_status()
    is_stale = True
    if status.get("timestamp"):
        try:
            ts_val = datetime.fromisoformat(status["timestamp"])
            is_stale = (datetime.now() - ts_val).total_seconds() > 300
        except (ValueError, TypeError):
            is_stale = True

    heartbeat_class = "heartbeat-stale" if is_stale else "heartbeat-dot"

    html = """<!DOCTYPE html>
<html>
<head>
    <title>Factory Quality Iteration Loop - Telemetry</title>
    <meta http-equiv="refresh" content="5">
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
        .refresh-time { color: #666; font-size: 11px; margin-top: 20px; }
        .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 15px 0; }
        .kpi-cell { background: #2d2d2d; padding: 10px 12px; border-radius: 8px; text-align: center; }
        .kpi-label { color: #888; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
        .kpi-value { font-size: 20px; font-weight: bold; margin: 4px 0; }
        .kpi-delta { font-size: 11px; color: #888; }
        .delta-up { color: #4caf50; }
        .delta-down { color: #f44336; }
        .delta-flat { color: #666; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        @keyframes fade-in { from { opacity: 0.8; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
        .pulse-active { animation: pulse 2s ease-in-out infinite; }
        .recently-changed { animation: fade-in 1s ease-out; }
        .heartbeat-dot { display: inline-block; color: #4caf50; animation: pulse 2s ease-in-out infinite; margin-right: 4px; }
        .heartbeat-stale { display: inline-block; color: #666; margin-right: 4px; }
        .iteration-timeline { margin: 15px 0; padding: 15px 20px; background: #252525; border-radius: 10px; }
        .timeline-track { display: flex; align-items: center; justify-content: space-between; position: relative; padding: 10px 0; }
        .timeline-track::before { content: ''; position: absolute; top: 50%; left: 0; right: 0; height: 2px; background: #444; transform: translateY(-50%); z-index: 0; }
        .timeline-marker { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; }
        .timeline-dot { width: 16px; height: 16px; border-radius: 50%; border: 2px solid transparent; }
        .timeline-dot-latest { width: 20px; height: 20px; border: 2px solid #4fc3f7; box-shadow: 0 0 8px rgba(79, 195, 247, 0.4); }
        .timeline-label { font-size: 10px; color: #888; }
        .timeline-title { color: #888; font-size: 12px; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px; }
    </style>
</head>
<body>
    <h1>Factory Quality Iteration Loop</h1>
    <div class="refresh-time"><span class=\"""" + heartbeat_class + """\">●</span>Last updated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """ (auto-refreshes every 5s)</div>
"""

    html += _live_status_section()

    status = _read_live_status()
    if status.get("gpu_util_pct") is not None or status.get("gpu_mem_used_mb"):
        gpu_util = status.get("gpu_util_pct", "?")
        gpu_mem = status.get("gpu_mem_used_mb", "?")
        gpu_total = status.get("gpu_mem_total_mb", "?")
        html += f'''
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
        <div class="metric"><div class="metric-label">GPU Utilization</div>
            <div class="metric-value" style="color:{'#4caf50' if isinstance(gpu_util, int) and gpu_util > 50 else '#ff9800'}">{gpu_util}%</div></div>
        <div class="metric"><div class="metric-label">GPU Memory</div>
            <div class="metric-value">{gpu_mem} / {gpu_total} MB</div></div>
    </div>
'''

    html += _video_outputs_section()

    html += _iteration_timeline_section(iterations)

    deltas = _compute_deltas(iterations)
    
    def render_delta(key):
        if not deltas or key not in deltas:
            return "&nbsp;"
        arrow, cls, _ = deltas[key]
        return f'<span class="kpi-delta {cls}">{arrow}</span>'

    def get_delta_class(key):
        if not deltas or key not in deltas:
            return ""
        arrow, cls, _ = deltas[key]
        if cls in ["up", "down"]:
            return "recently-changed"
        return ""

    if iterations:
        latest = iterations[-1]
        identity_sim = latest.get('metrics_summary', {}).get('identity_similarity', 0)
        ssim = latest.get('metrics_summary', {}).get('ssim', 0)
        cost = latest.get('cost_so_far', 0)
        status = latest.get('status', 'unknown')

        html += f"""
    <div class="kpi-grid">
        <div class="kpi-cell">
            <div class="kpi-label">Total Iterations</div>
            <div class="kpi-value">{len(iterations)}</div>
            <div class="kpi-delta">&nbsp;</div>
        </div>

        <div class="kpi-cell {get_delta_class('identity')}">
            <div class="kpi-label">Identity</div>
            <div class="kpi-value {'pass' if identity_sim >= 0.65 else 'fail'}">{identity_sim:.4f}</div>
            <div class="kpi-delta">{render_delta('identity')}</div>
        </div>

        <div class="kpi-cell {get_delta_class('ssim')}">
            <div class="kpi-label">SSIM</div>
            <div class="kpi-value {'pass' if ssim >= 0.70 else 'fail'}">{ssim:.4f}</div>
            <div class="kpi-delta">{render_delta('ssim')}</div>
        </div>

        <div class="kpi-cell {get_delta_class('cost')}">
            <div class="kpi-label">Cost</div>
            <div class="kpi-value">${cost:.2f}</div>
            <div class="kpi-delta">{render_delta('cost')}</div>
        </div>

        <div class="kpi-cell">
            <div class="kpi-label">Status</div>
            <div class="kpi-value">
                <span class="status-badge status-{status}">{status.upper()}</span>
            </div>
            <div class="kpi-delta">&nbsp;</div>
        </div>
    </div>
"""

    if iterations:
        latest = iterations[-1]
        identity_sim = latest.get('metrics_summary', {}).get('identity_similarity', 0)
        ssim = latest.get('metrics_summary', {}).get('ssim', 0)
        cost = latest.get('cost_so_far', 0)
        status = latest.get('status', 'unknown')



        html += _result_images_section()

        html += """
    <h2>Iteration History</h2>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Time</th>
                <th>Identity</th>
                <th>SSIM</th>
                <th>Status</th>
                <th>Cost</th>
                <th>Changes</th>
            </tr>
        </thead>
        <tbody>
"""

        for it in reversed(iterations[-20:]):
            num = it.get('iteration_number', 0)
            ts = it.get('timestamp', 'N/A')
            metrics = it.get('metrics_summary', {})
            identity = metrics.get('identity_similarity', 0)
            it_ssim = metrics.get('ssim', 0)
            stat = it.get('status', 'unknown')
            cost_it = it.get('cost_so_far', 0)
            changes = it.get('changes_made', 'N/A')
            if len(changes) > 60:
                changes = changes[:57] + "..."

            html += f"""
            <tr>
                <td>{num}</td>
                <td>{ts}</td>
                <td class="{'pass' if identity >= 0.65 else 'fail'}">{identity:.4f}</td>
                <td class="{'pass' if it_ssim >= 0.70 else 'fail'}">{it_ssim:.4f}</td>
                <td><span class="status-badge status-{stat}">{stat}</span></td>
                <td>${cost_it:.2f}</td>
                <td style="font-size:12px;">{changes}</td>
            </tr>
"""

        html += """
        </tbody>
    </table>
"""

        html += f"""
    <h2>Latest Iteration Details</h2>
    <div class="iteration-card">
        <h3>Iteration {latest.get('iteration_number', 0)} - {latest.get('status', 'unknown').upper()}</h3>
        <p><strong>Changes Made:</strong> {latest.get('changes_made', 'N/A')}</p>
        <p><strong>Diagnosis:</strong> {latest.get('diagnosis', {}).get('summary', 'N/A')}</p>
        <p><strong>Git Commit:</strong> <code>{latest.get('git_commit_hash', 'N/A')}</code></p>
    </div>
"""
    else:
        html += """
    <div class="kpi-grid">
        <div class="kpi-cell" style="grid-column: span 5;">
            <div class="kpi-label">Status</div>
            <div class="kpi-value pending">Waiting for first iteration...</div>
        </div>
    </div>
"""

    html += _multi_source_section()
    html += _archive_gallery()

    html += """
</body>
</html>
"""

    return html


def _multi_source_section() -> str:
    summary_path = Path("factory/results/sam_multi_source_summary.json")
    grid_path = Path("factory/results/sam_multi_source_grid.png")

    if not summary_path.exists():
        return ""

    with open(summary_path) as f:
        summary = json.load(f)

    results = summary.get("results", [])
    if not results:
        return ""

    html = '<h2>Multi-Source Test (Sam Images)</h2>\n'
    html += f'<div class="metric"><div class="metric-label">Best Source</div>'
    html += f'<div class="metric-value">{summary.get("best_source", "?")} — {summary.get("best_identity", 0):.4f}</div></div>\n'
    html += f'<div class="metric"><div class="metric-label">Average Identity</div>'
    html += f'<div class="metric-value">{summary.get("average_identity", 0):.4f} across {len(results)} sources</div></div>\n'

    if grid_path.exists():
        grid_uri = _img_to_data_uri(grid_path)
        html += f'<img src="{grid_uri}" alt="Multi-source comparison grid" style="width:100%;border-radius:8px;margin:10px 0;">\n'

    html += """<table><thead><tr><th>Source</th><th>Identity</th><th>Time</th><th>Status</th></tr></thead><tbody>\n"""
    for r in sorted(results, key=lambda x: -x["identity"]):
        cls = "pass" if r["identity"] >= 0.65 else "fail"
        html += f'<tr><td>{r["source"]}</td><td class="{cls}">{r["identity"]:.4f}</td>'
        html += f'<td>{r["time"]:.1f}s</td><td class="{cls}">{"PASS" if r["identity"] >= 0.65 else "FAIL"}</td></tr>\n'
    html += "</tbody></table>\n"

    return html


def main():
    _sync_live_status()
    _sync_videos()
    html = generate_html()
    output_path = Path("factory/telemetry.html")
    output_path.write_text(html)
    print(f"Telemetry dashboard updated: {output_path.absolute()}")


if __name__ == "__main__":
    main()
