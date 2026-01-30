import numpy as np
import cv2
import pytest
from watserface.processors.modules.lip_fringe import apply_lip_fringe

@pytest.fixture
def synthetic_data():
    height, width = 200, 200
    dirty_swap = np.full((height, width, 3), 128, dtype=np.uint8) # Gray
    cv2.ellipse(dirty_swap, (100, 100), (40, 20), 0, 0, 360, (50, 50, 200), -1) # Red lips
    
    occlusion_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.rectangle(occlusion_mask, (90, 50), (110, 150), 1.0, -1)
    
    landmarks = np.zeros((68, 2), dtype=np.int32)
    center = (100, 100)
    axes = (40, 20)
    for i in range(20):
        angle = (i / 20.0) * 2 * np.pi
        x = int(center[0] + axes[0] * np.cos(angle))
        y = int(center[1] + axes[1] * np.sin(angle))
        landmarks[48+i] = [x, y]
        
    return dirty_swap, occlusion_mask.astype(np.float32), landmarks

def test_apply_lip_fringe_pixels(synthetic_data):
    dirty_swap, occlusion_mask, landmarks = synthetic_data
    fringe_color = (0, 255, 0) # Green
    
    result = apply_lip_fringe(
        dirty_swap.copy(), 
        occlusion_mask,
        landmarks, 
        fringe_width=5, 
        lip_color=fringe_color
    )
    
    # Check pixels
    p_inside_occ = result[100, 95] # x=95 is inside occlusion (unchanged)
    p_fringe = result[100, 88]     # x=88 is inside fringe (modified)
    p_outside = result[100, 80]    # x=80 is outside fringe (unchanged)
    
    assert np.allclose(p_inside_occ, [50, 50, 200]), "Inside occlusion should be unchanged"
    assert np.allclose(p_outside, [50, 50, 200]), "Outside fringe should be unchanged"
    
    # Fringe should be greenish
    assert p_fringe[1] > 60, f"Fringe G channel should increase, got {p_fringe[1]}"
    assert p_fringe[2] < 190, f"Fringe R channel should decrease, got {p_fringe[2]}"

def test_color_sampling_excludes_occlusion():
    height, width = 200, 200
    dirty_swap = np.full((height, width, 3), 128, dtype=np.uint8)
    cv2.ellipse(dirty_swap, (100, 100), (40, 20), 0, 0, 360, (50, 50, 200), -1)
    
    occlusion_mask = np.zeros((height, width), dtype=np.float32)
    cv2.rectangle(occlusion_mask, (110, 85), (140, 115), 1.0, -1)
    
    landmarks = np.zeros((68, 2), dtype=np.int32)
    center = (100, 100)
    axes = (40, 20)
    for i in range(20):
        angle = (i / 20.0) * 2 * np.pi
        x = int(center[0] + axes[0] * np.cos(angle))
        y = int(center[1] + axes[1] * np.sin(angle))
        landmarks[48+i] = [x, y]
    
    dirty_swap_with_green = dirty_swap.copy()
    cv2.rectangle(dirty_swap_with_green, (110, 85), (140, 115), (0, 255, 0), -1)
    
    result = apply_lip_fringe(
        dirty_swap_with_green,
        occlusion_mask,
        landmarks,
        fringe_width=5,
        lip_color=None
    )
    
    fringe_region = result[95:105, 85:95]
    mean_green = np.mean(fringe_region[:, :, 1])
    
    assert mean_green < 150, f"Fringe should not sample from green occlusion, got mean G={mean_green}"

def test_alpha_cap():
    height, width = 200, 200
    dirty_swap = np.full((height, width, 3), 100, dtype=np.uint8)
    cv2.ellipse(dirty_swap, (100, 100), (40, 20), 0, 0, 360, (50, 50, 200), -1)
    
    occlusion_mask = np.zeros((height, width), dtype=np.float32)
    cv2.rectangle(occlusion_mask, (90, 50), (110, 150), 1.0, -1)
    
    landmarks = np.zeros((68, 2), dtype=np.int32)
    center = (100, 100)
    axes = (40, 20)
    for i in range(20):
        angle = (i / 20.0) * 2 * np.pi
        x = int(center[0] + axes[0] * np.cos(angle))
        y = int(center[1] + axes[1] * np.sin(angle))
        landmarks[48+i] = [x, y]
    
    fringe_color = (0, 255, 0)
    result = apply_lip_fringe(
        dirty_swap.copy(),
        occlusion_mask,
        landmarks,
        fringe_width=5,
        lip_color=fringe_color
    )
    
    diff = np.abs(result.astype(np.float32) - dirty_swap.astype(np.float32)) / 255.0
    max_diff = np.max(diff)
    
    assert max_diff <= 0.6, f"Max alpha blend should be capped at 0.6, got {max_diff}"
