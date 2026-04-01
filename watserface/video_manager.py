from collections import OrderedDict
from typing import Optional

import cv2

from watserface.types import VideoPoolSet


class BoundedVideoPool(OrderedDict):
    def __init__(self, maxsize: int = 64) -> None:
        super().__init__()
        self.maxsize = maxsize

    def __setitem__(self, key: str, value: cv2.VideoCapture) -> None:
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            _, video_capture = self.popitem(last=False)
            video_capture.release()

    def get(
        self, key: str, default: Optional[cv2.VideoCapture] = None
    ) -> Optional[cv2.VideoCapture]:
        if key in self:
            self.move_to_end(key)
            return super().__getitem__(key)
        return default


VIDEO_POOL_SET: VideoPoolSet = BoundedVideoPool()


def get_video_capture(video_path: str) -> cv2.VideoCapture:
    if video_path not in VIDEO_POOL_SET:
        VIDEO_POOL_SET[video_path] = cv2.VideoCapture(video_path)

    return VIDEO_POOL_SET.get(video_path)


def clear_video_pool() -> None:
    for video_capture in VIDEO_POOL_SET.values():
        video_capture.release()

    VIDEO_POOL_SET.clear()
