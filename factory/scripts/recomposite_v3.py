#!/usr/bin/env python3
"""
Multi-band Laplacian pyramid compositing with boundary-ring LAB color matching
and temporal EMA smoothing for seam-free face swap paste-back.
"""
import os
import sys
import json
import time
import numpy as np
import cv2
from PIL import Image
from datetime import datetime

BASE = '/workspace/watserface/vendors/REFace/results_video'
MODEL_OUTPUTS = os.path.join(BASE, 'watserface_run/model_outputs')
TARGET_FRAMES = os.path.join(BASE, 'zBambola')
MASK_FRAMES = os.path.join(BASE, 'zBambolamask_frames')
INV_TRANSFORMS = os.path.join(BASE, 'zBambola_inv_transforms.npy')
OUTPUT_DIR = '/workspace/watserface/factory/results/recomposited_v3'
STATUS_PATH = '/workspace/watserface/factory/results/live_status.json'

FACE_LABELS = np.array([2, 3, 4, 5, 6, 7, 8, 11], dtype=np.uint8)

PARSE_DILATE = 41
PARSE_CLOSE = 31
CORE_ERODE = 31
OUTER_DILATE = 57
EDGE_INSET_FRAC = 0.06
EDGE_SIGMA = 18.0
ALPHA_SIGMA = 16.0
COLOR_EMA = 0.82
MASK_EMA = 0.70
PYR_LEVELS = 5


def write_status(phase, detail, progress=0, total=0):
    s = {
        'timestamp': datetime.now().isoformat(),
        'phase': phase, 'detail': detail,
        'progress': progress, 'total': total,
        'pct': round(progress / total * 100, 1) if total > 0 else 0,
        'pid': os.getpid(),
    }
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    with open(STATUS_PATH, 'w') as f:
        json.dump(s, f, indent=2)


def _robust_mean_std(values):
    if values.size == 0:
        return 0.0, 1.0
    if values.size < 32:
        return float(values.mean()), float(values.std() + 1e-6)
    lo, hi = np.percentile(values, (5, 95))
    clipped = values[(values >= lo) & (values <= hi)]
    if clipped.size < 32:
        clipped = values
    return float(clipped.mean()), float(clipped.std() + 1e-6)


def _laplacian_pyramid(img, levels):
    gp = [img.astype(np.float32)]
    for _ in range(levels):
        gp.append(cv2.pyrDown(gp[-1]))
    lp = []
    for i in range(levels):
        up = cv2.pyrUp(gp[i + 1], dstsize=(gp[i].shape[1], gp[i].shape[0]))
        lp.append(gp[i] - up)
    lp.append(gp[-1])
    return lp


def _gaussian_pyramid(mask, levels):
    gp = [mask.astype(np.float32)]
    for _ in range(levels):
        gp.append(cv2.pyrDown(gp[-1]))
    return gp


def composite_frame(target_bgr, face_crop_bgr, parsing_mask_512, pil_inv_coeffs, state):
    h_t, w_t = target_bgr.shape[:2]
    h_c, w_c = face_crop_bgr.shape[:2]

    # 1) Build crop-space alpha from parsing + ellipse + edge suppression
    if parsing_mask_512 is None:
        parse_face = np.zeros((h_c, w_c), dtype=np.uint8)
    else:
        pm = parsing_mask_512
        if pm.ndim == 3:
            pm = pm[:, :, 0]
        pm = cv2.resize(pm.astype(np.uint8), (w_c, h_c), interpolation=cv2.INTER_NEAREST)
        parse_face = np.isin(pm, FACE_LABELS).astype(np.uint8)
        k_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (PARSE_DILATE, PARSE_DILATE))
        k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (PARSE_CLOSE, PARSE_CLOSE))
        parse_face = cv2.dilate(parse_face, k_dilate, iterations=1)
        parse_face = cv2.morphologyEx(parse_face, cv2.MORPH_CLOSE, k_close)

    ellipse = np.zeros((h_c, w_c), dtype=np.uint8)
    cv2.ellipse(ellipse, (w_c // 2, h_c // 2),
                (int(0.47 * w_c), int(0.49 * h_c)), 0, 0, 360, 1, -1)

    support = np.maximum(parse_face, ellipse)

    inset = max(int(round(EDGE_INSET_FRAC * min(h_c, w_c))), 24)
    edge_box = np.zeros((h_c, w_c), dtype=np.float32)
    edge_box[inset:h_c - inset, inset:w_c - inset] = 1.0
    edge_box = cv2.GaussianBlur(edge_box, (0, 0), EDGE_SIGMA)

    support = (support.astype(np.float32) * edge_box > 0.05).astype(np.uint8)

    core_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CORE_ERODE, CORE_ERODE))
    outer_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (OUTER_DILATE, OUTER_DILATE))
    core = cv2.erode(support, core_k, iterations=1)
    outer = cv2.dilate(support, outer_k, iterations=1)
    outer = (outer.astype(np.float32) * (edge_box > 0.02).astype(np.float32)).astype(np.uint8)

    alpha_crop = cv2.GaussianBlur(outer.astype(np.float32), (0, 0), ALPHA_SIGMA)
    alpha_crop[core > 0] = 1.0
    alpha_crop = np.clip(alpha_crop, 0.0, 1.0)

    prev_alpha = state.get("alpha_crop")
    if isinstance(prev_alpha, np.ndarray) and prev_alpha.shape == alpha_crop.shape:
        alpha_crop = prev_alpha * MASK_EMA + alpha_crop * (1.0 - MASK_EMA)
    state["alpha_crop"] = alpha_crop.copy()

    # 2) Perspective matrices
    a, b, c, d, e, f, g, h = [float(x) for x in pil_inv_coeffs]
    m_pil = np.array([[a, b, c], [d, e, f], [g, h, 1.0]], dtype=np.float64)
    m_crop_to_target = np.linalg.inv(m_pil)
    m_target_to_crop = np.linalg.inv(m_crop_to_target)

    # 3) Boundary-ring LAB color matching
    target_in_crop = cv2.warpPerspective(
        target_bgr, m_target_to_crop, (w_c, h_c),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    ring = (alpha_crop > 0.20) & (alpha_crop < 0.85)
    if ring.sum() < 800:
        ring = (alpha_crop > 0.10) & (alpha_crop < 0.95)
    if ring.sum() < 800:
        ring = support > 0

    face_lab = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    tgt_lab = cv2.cvtColor(target_in_crop, cv2.COLOR_BGR2LAB).astype(np.float32)

    gain = np.ones(3, dtype=np.float32)
    bias = np.zeros(3, dtype=np.float32)
    gain_min = np.array([0.85, 0.90, 0.90], dtype=np.float32)
    gain_max = np.array([1.15, 1.10, 1.10], dtype=np.float32)
    bias_min = np.array([-18.0, -10.0, -10.0], dtype=np.float32)
    bias_max = np.array([18.0, 10.0, 10.0], dtype=np.float32)

    for ch in range(3):
        src_vals = face_lab[:, :, ch][ring]
        tgt_vals = tgt_lab[:, :, ch][ring]
        src_mean, src_std = _robust_mean_std(src_vals)
        tgt_mean, tgt_std = _robust_mean_std(tgt_vals)
        g_ch = tgt_std / src_std
        b_ch = tgt_mean - g_ch * src_mean
        gain[ch] = np.clip(g_ch, gain_min[ch], gain_max[ch])
        bias[ch] = np.clip(b_ch, bias_min[ch], bias_max[ch])

    prev_gain = state.get("gain")
    prev_bias = state.get("bias")
    if isinstance(prev_gain, np.ndarray) and prev_gain.shape == (3,):
        gain = prev_gain * COLOR_EMA + gain * (1.0 - COLOR_EMA)
    if isinstance(prev_bias, np.ndarray) and prev_bias.shape == (3,):
        bias = prev_bias * COLOR_EMA + bias * (1.0 - COLOR_EMA)
    state["gain"] = gain.copy()
    state["bias"] = bias.copy()

    corrected_lab = face_lab.copy()
    for ch in range(3):
        corrected_lab[:, :, ch] = face_lab[:, :, ch] * gain[ch] + bias[ch]
    corrected_lab = np.clip(corrected_lab, 0.0, 255.0)

    # Stronger correction near boundary, milder in center
    boundary_w = np.clip((0.92 - alpha_crop) / 0.92, 0.0, 1.0)
    boundary_w = np.power(boundary_w, 0.7)
    boundary_w = cv2.GaussianBlur(boundary_w, (0, 0), 5.0)
    color_mix = (0.20 + 0.80 * boundary_w)[..., None]

    mixed_lab = face_lab * (1.0 - color_mix) + corrected_lab * color_mix
    mixed_lab = np.clip(mixed_lab, 0.0, 255.0).astype(np.uint8)
    corrected_face_bgr = cv2.cvtColor(mixed_lab, cv2.COLOR_LAB2BGR)

    # 4) Warp to target space
    warped_face = cv2.warpPerspective(
        corrected_face_bgr, m_crop_to_target, (w_t, h_t),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    alpha_raw = cv2.warpPerspective(
        alpha_crop, m_crop_to_target, (w_t, h_t),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
    alpha_raw = np.clip(alpha_raw.astype(np.float32), 0.0, 1.0)

    # 5) Edge-aware alpha refinement (guided filter or bilateral fallback)
    guide = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    try:
        alpha_refined = cv2.ximgproc.guidedFilter(
            guide=guide, src=alpha_raw, radius=9, eps=1e-4)
    except AttributeError:
        alpha_refined = cv2.bilateralFilter(alpha_raw, d=7, sigmaColor=0.1, sigmaSpace=7)

    alpha = 0.7 * alpha_refined + 0.3 * alpha_raw
    alpha = cv2.GaussianBlur(alpha, (0, 0), 1.2)
    alpha = np.clip(alpha, 0.0, 1.0).astype(np.float32)

    # 6) Laplacian pyramid multi-band blend
    max_levels = max(1, int(np.floor(np.log2(min(h_t, w_t)))) - 2)
    levels = min(PYR_LEVELS, max_levels)

    lp_tgt = _laplacian_pyramid(target_bgr, levels)
    lp_face = _laplacian_pyramid(warped_face, levels)
    gp_alpha = _gaussian_pyramid(alpha, levels)

    blended_pyr = []
    for l_face, l_tgt, m in zip(lp_face, lp_tgt, gp_alpha):
        m3 = m[..., None]
        blended_pyr.append(l_face * m3 + l_tgt * (1.0 - m3))

    out = blended_pyr[-1]
    for i in range(levels - 1, -1, -1):
        out = cv2.pyrUp(out, dstsize=(blended_pyr[i].shape[1], blended_pyr[i].shape[0]))
        out = out + blended_pyr[i]

    return np.clip(out, 0.0, 255.0).astype(np.uint8), state


def main():
    t_start = time.time()
    write_status('init', 'v3: Laplacian pyramid + LAB color match + temporal EMA')
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    inv_transforms = np.load(INV_TRANSFORMS, allow_pickle=True)
    available = sorted([f for f in os.listdir(MODEL_OUTPUTS) if f.endswith('.png')])
    n = len(available)
    print(f'{n} frames to composite')
    write_status('compositing', f'0/{n} frames', 0, n)

    state = {}
    for i, fname in enumerate(available):
        idx = int(fname.replace('.png', ''))

        crop_cv = cv2.imread(os.path.join(MODEL_OUTPUTS, fname))
        target_cv = cv2.imread(os.path.join(TARGET_FRAMES, f'{idx}.png'))
        mask_path = os.path.join(MASK_FRAMES, f'{idx}.png')
        parsing = np.array(Image.open(mask_path)) if os.path.exists(mask_path) else None

        result, state = composite_frame(
            target_cv, crop_cv, parsing, inv_transforms[idx], state)

        cv2.imwrite(os.path.join(OUTPUT_DIR, f'{idx:012d}.png'), result)

        if (i + 1) % 10 == 0 or i == n - 1:
            write_status('compositing', f'{i+1}/{n} frames', i + 1, n)
            print(f'  {i+1}/{n}')

    write_status('encode', f'Encoding {n} frames to H.264')
    out_path = '/workspace/watserface/factory/results/video_swap_softmask_h264.mp4'
    os.system(
        f'ffmpeg -y -framerate 24 -i "{OUTPUT_DIR}/%012d.png" '
        f'-c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p "{out_path}" 2>/dev/null'
    )

    elapsed = time.time() - t_start
    if os.path.exists(out_path):
        mb = os.path.getsize(out_path) / (1024 * 1024)
        write_status('done', f'v3 complete! {n} frames, {elapsed:.0f}s, {mb:.1f}MB', n, n)
        print(f'Output: {out_path} ({mb:.1f}MB, {elapsed:.0f}s)')
    else:
        write_status('error', 'Video encoding failed')


if __name__ == '__main__':
    main()
