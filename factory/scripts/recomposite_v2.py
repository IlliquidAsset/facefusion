#!/usr/bin/env python3
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
OUTPUT_DIR = '/workspace/watserface/factory/results/recomposited_v2'
STATUS_PATH = '/workspace/watserface/factory/results/live_status.json'

FEATHER_RADIUS = 55
COLOR_STRENGTH = 0.25


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


def create_blending_mask(parsing_mask_path, crop_size=1024):
    h, w = crop_size, crop_size

    # Face fills nearly the entire 1024x1024 crop, so the mask must cover ~90%
    # with feathered falloff only at the extreme edges.
    # Start with a full-white image, then erode inward and blur to create
    # a soft border that fades to 0 only at the very edge of the crop.
    border = 80
    mask = np.zeros((h, w), dtype=np.float32)
    mask[border:h - border, border:w - border] = 1.0
    mask = cv2.GaussianBlur(mask, (0, 0), FEATHER_RADIUS)

    if parsing_mask_path and os.path.exists(parsing_mask_path):
        seg = np.array(Image.open(parsing_mask_path).resize((crop_size, crop_size), Image.NEAREST))
        face_mask = (seg > 0).astype(np.float32)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
        face_mask = cv2.dilate(face_mask, kernel, iterations=3)
        face_mask = cv2.GaussianBlur(face_mask, (0, 0), FEATHER_RADIUS)
        mask = np.maximum(mask, face_mask)

    return np.clip(mask, 0.0, 1.0)


def color_transfer_lab(source, target, mask, strength=0.25):
    if strength <= 0:
        return source
    src_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float32)
    tgt_lab = cv2.cvtColor(target, cv2.COLOR_BGR2LAB).astype(np.float32)
    mask_bool = mask > 0.5
    if mask_bool.sum() < 100:
        return source
    for ch in range(3):
        src_mean = src_lab[:, :, ch][mask_bool].mean()
        src_std = src_lab[:, :, ch][mask_bool].std() + 1e-6
        tgt_mean = tgt_lab[:, :, ch][mask_bool].mean()
        tgt_std = tgt_lab[:, :, ch][mask_bool].std() + 1e-6
        shifted = (src_lab[:, :, ch] - src_mean) * (tgt_std / src_std) + tgt_mean
        src_lab[:, :, ch] = src_lab[:, :, ch] * (1 - strength) + shifted * strength
    return cv2.cvtColor(np.clip(src_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def composite_frame(frame_idx, inv_transforms):
    crop_path = os.path.join(MODEL_OUTPUTS, f'{frame_idx:012d}.png')
    target_path = os.path.join(TARGET_FRAMES, f'{frame_idx}.png')
    mask_path = os.path.join(MASK_FRAMES, f'{frame_idx}.png')

    if not os.path.exists(crop_path) or not os.path.exists(target_path):
        return None

    crop_cv = cv2.cvtColor(np.array(Image.open(crop_path).convert('RGB')), cv2.COLOR_RGB2BGR)
    target_cv = cv2.cvtColor(np.array(Image.open(target_path).convert('RGB')), cv2.COLOR_RGB2BGR)

    h_t, w_t = target_cv.shape[:2]
    h_c, w_c = crop_cv.shape[:2]

    blend_mask = create_blending_mask(mask_path, crop_size=h_c)

    inv_coeffs = inv_transforms[frame_idx]
    a, b, c, d, e, f, g, h = inv_coeffs
    M_inv = np.array([[a, b, c], [d, e, f], [g, h, 1.0]], dtype=np.float64)
    M = np.linalg.inv(M_inv)

    M_inv_cv = np.linalg.inv(M)
    target_in_crop = cv2.warpPerspective(target_cv, M_inv_cv, (w_c, h_c),
                                          flags=cv2.INTER_LINEAR,
                                          borderMode=cv2.BORDER_REFLECT)
    small_ellipse = np.zeros((h_c, w_c), dtype=np.float32)
    cv2.ellipse(small_ellipse, (w_c // 2, h_c // 2),
                (int(w_c * 0.3), int(h_c * 0.3)), 0, 0, 360, 1.0, -1)
    small_ellipse = cv2.GaussianBlur(small_ellipse, (0, 0), 20)
    crop_cv = color_transfer_lab(crop_cv, target_in_crop, small_ellipse, COLOR_STRENGTH)

    warped_face = cv2.warpPerspective(crop_cv, M, (w_t, h_t),
                                       flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    warped_mask = cv2.warpPerspective(blend_mask, M, (w_t, h_t),
                                       flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    m3 = warped_mask[:, :, np.newaxis]
    result = (target_cv.astype(np.float32) * (1 - m3) + warped_face.astype(np.float32) * m3)
    return np.clip(result, 0, 255).astype(np.uint8)


def main():
    t_start = time.time()
    write_status('init', 'Re-compositing v2: parsing+ellipse union mask')
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    inv_transforms = np.load(INV_TRANSFORMS, allow_pickle=True)
    available = sorted([f for f in os.listdir(MODEL_OUTPUTS) if f.endswith('.png')])
    n = len(available)
    print(f'{n} frames to composite')
    write_status('compositing', f'0/{n} frames', 0, n)

    for i, fname in enumerate(available):
        idx = int(fname.replace('.png', ''))
        result = composite_frame(idx, inv_transforms)
        if result is not None:
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
        write_status('done', f'Complete! {n} frames, {elapsed:.0f}s, {mb:.1f}MB', n, n)
        print(f'Output: {out_path} ({mb:.1f}MB, {elapsed:.0f}s)')
    else:
        write_status('error', 'Video encoding failed')


if __name__ == '__main__':
    main()
