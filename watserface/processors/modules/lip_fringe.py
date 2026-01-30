import cv2
import numpy as np
from typing import Optional, Tuple

BLEND_STRENGTH = 0.6

def apply_lip_fringe(
    dirty_swap: np.ndarray,
    occlusion_mask: np.ndarray,
    landmarks: np.ndarray,
    fringe_width: int = 5,
    lip_color: Optional[Tuple[int, int, int]] = None
) -> np.ndarray:
    """
    Applies a lip-colored fringe along the occlusion boundary in the lip region.
    
    This technique helps "sell" the wrapping of lips around an object (like a corndog)
    by painting a fake contact shadow/fringe on the face side of the occlusion.
    
    Args:
        dirty_swap: The swapped face image (BGR) that will be under the occlusion.
        occlusion_mask: The alpha mask of the occlusion (0.0=face, 1.0=occlusion).
                        This should be the mask used for final compositing.
        landmarks: 68-point face landmarks (numpy array).
        fringe_width: Width of the fringe band in pixels.
        lip_color: Optional fixed color (B, G, R). If None, samples from lip center.
        
    Returns:
        The modified dirty_swap image with the fringe applied. 
        (Note: You should composite the occlusion ON TOP of this result). 
    """
    if landmarks.shape[0] < 68:
        return dirty_swap
    
    height, width = dirty_swap.shape[:2]
    
    # Ensure mask is suitable for cv2 operations (0-255 uint8)
    if occlusion_mask.dtype != np.uint8:
        mask_uint8 = (occlusion_mask * 255).astype(np.uint8)
    else:
        mask_uint8 = occlusion_mask
        
    # 1. Create the Fringe Band (Mask Expansion)
    # We want the area *outside* the occlusion (on the face) that touches the occlusion.
    # Dilate the occlusion mask to expand it into the face area.
    kernel_size = fringe_width * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    dilated_mask = cv2.dilate(mask_uint8, kernel, iterations=1)
    
    # Subtract the original occlusion mask to get just the new band
    # (We only care about pixels that are NOT currently occlusion, but ARE near it)
    # Note: In the final composite, the occlusion_mask area will be replaced by the original image.
    # So we strictly paint on (1 - occlusion_mask).
    fringe_band = cv2.subtract(dilated_mask, mask_uint8)
    
    # 2. Restrict to Lip Region
    # Create a mask from lip landmarks (48-67)
    lip_points = landmarks[48:68].astype(np.int32)
    lip_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(lip_mask, cv2.convexHull(lip_points), 255)
    
    # Expand lip mask slightly to catch the edge
    lip_mask = cv2.dilate(lip_mask, np.ones((5,5), np.uint8), iterations=1)
    
    # Intersect fringe band with lip mask
    active_fringe = cv2.bitwise_and(fringe_band, lip_mask)
    
    # If no fringe in lip area, return early
    if cv2.countNonZero(active_fringe) == 0:
        return dirty_swap
    
    # Calculate distance from the occlusion boundary into the face region
    # Invert mask: 0=occlusion, 255=face
    inv_occlusion = cv2.bitwise_not(mask_uint8)
        
    # 3. Determine Lip Color
    if lip_color is None:
        # Sample color from the dirty swap within the lip region
        # (excluding the fringe area itself to avoid sampling the background/occlusion if possible, 
        # though dirty_swap shouldn't have the occlusion anyway)
        
        # Use a smaller eroded lip mask for sampling to get "core" lip color
        sample_mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillConvexPoly(sample_mask, cv2.convexHull(lip_points), 255)
        # Erode to avoid edges
        sample_mask = cv2.erode(sample_mask, np.ones((3,3), np.uint8), iterations=1)
        
        # Exclude occluded pixels from sampling
        sample_mask = cv2.bitwise_and(sample_mask, inv_occlusion)
        
        # Fallback: if sample_mask is too small, sample from landmark 66 (inner lower lip)
        if cv2.countNonZero(sample_mask) < 20:
            pixel = dirty_swap[landmarks[66][1], landmarks[66][0]]
            lip_color = (int(pixel[0]), int(pixel[1]), int(pixel[2]))
        else:
            mean_color = cv2.mean(dirty_swap, mask=sample_mask)[:3]
            lip_color = (int(mean_color[0]), int(mean_color[1]), int(mean_color[2]))
        
    # 4. Paint the Fringe with Distance-Based Falloff
    # We want alpha to be high near the occlusion (inner edge of fringe)
    # and low at the outer edge of the fringe.
    # Distance to nearest zero pixel (occlusion boundary)
    dist_map = cv2.distanceTransform(inv_occlusion, cv2.DIST_L2, 5)
    
    # Normalize distance: 1.0 at boundary, decreasing as we go out
    # dist starts > 0. Pixels adjacent to occlusion are usually dist ~ 1.0
    falloff_alpha = np.clip(1.0 - ((dist_map - 1.0) / fringe_width), 0.0, 1.0)
    
    # Mask to just the active fringe region
    active_fringe_float = active_fringe.astype(np.float32) / 255.0
    final_alpha = falloff_alpha * active_fringe_float * BLEND_STRENGTH
    
    # Create color layer
    color_layer = np.full_like(dirty_swap, lip_color, dtype=np.uint8)
    
    # Composite
    alpha_3ch = np.dstack([final_alpha] * 3)
    
    result = dirty_swap.astype(np.float32) * (1.0 - alpha_3ch) + \
             color_layer.astype(np.float32) * alpha_3ch
             
    return np.clip(result, 0, 255).astype(np.uint8)
