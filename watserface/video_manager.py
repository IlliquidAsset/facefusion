from collections import OrderedDict
from typing import Optional

import cv2

from watserface.types import VideoPoolSet

class BoundedVideoPool(OrderedDict[str, cv2.VideoCapture]):
	def __init__(self, maxsize : int = 64) -> None:
		super().__init__()
		self.maxsize = maxsize

	def __setitem__(self, key : str, value : cv2.VideoCapture) -> None:
		if key in self:
			self.move_to_end(key)
		super().__setitem__(key, value)
		if len(self) > self.maxsize:
			_, video_capture = self.popitem(last = False)
			if video_capture.isOpened():
				video_capture.release()

	def get(self, key : str, default : Optional[cv2.VideoCapture] = None) -> Optional[cv2.VideoCapture]:
		if key in self:
			self.move_to_end(key)
			return super().__getitem__(key)
		return default


VIDEO_POOL_SET : VideoPoolSet = BoundedVideoPool()


def get_video_capture(video_path : str) -> cv2.VideoCapture:
	if video_path not in VIDEO_POOL_SET:
		VIDEO_POOL_SET[video_path] = cv2.VideoCapture(video_path)

	# We know it exists now, but get() returns Optional.
	# The original signature of get_video_capture returns cv2.VideoCapture (not Optional)
	# So we should safely cast or assert.
	video_capture = VIDEO_POOL_SET.get(video_path)
	if video_capture is None:
		# Should not happen if we just added it
		raise RuntimeError(f"Failed to get video capture for {video_path}")
	return video_capture


def clear_video_pool() -> None:
	for video_capture in VIDEO_POOL_SET.values():
		video_capture.release()

	VIDEO_POOL_SET.clear()
