from collections import OrderedDict
from typing import List, Optional

from facefusion.hash_helper import create_hash
from facefusion.types import Face, FaceSet, FaceStore, VisionFrame

class BoundedStaticFaceCache(OrderedDict):
	def __init__(self, maxsize : int = 128) -> None:
		super().__init__()
		self.maxsize = maxsize

	def __setitem__(self, key : str, value : List[Face]) -> None:
		if key in self:
			self.move_to_end(key)
		super().__setitem__(key, value)
		if len(self) > self.maxsize:
			self.popitem(last = False)

	def get(self, key : str, default : Optional[List[Face]] = None) -> Optional[List[Face]]:
		if key in self:
			self.move_to_end(key)
			return super().__getitem__(key)
		return default

FACE_STORE : FaceStore =\
{
	'static_faces': BoundedStaticFaceCache(),
	'reference_faces': {}
}


def get_face_store() -> FaceStore:
	return FACE_STORE


def get_static_faces(vision_frame : VisionFrame) -> Optional[List[Face]]:
	vision_hash = create_hash(vision_frame.tobytes())
	return FACE_STORE.get('static_faces').get(vision_hash)


def set_static_faces(vision_frame : VisionFrame, faces : List[Face]) -> None:
	vision_hash = create_hash(vision_frame.tobytes())
	if vision_hash:
		FACE_STORE['static_faces'][vision_hash] = faces


def clear_static_faces() -> None:
	FACE_STORE['static_faces'].clear()


def get_reference_faces() -> Optional[FaceSet]:
	return FACE_STORE.get('reference_faces')


def append_reference_face(name : str, face : Face) -> None:
	if name not in FACE_STORE.get('reference_faces'):
		FACE_STORE['reference_faces'][name] = []
	FACE_STORE['reference_faces'][name].append(face)


def clear_reference_faces() -> None:
	FACE_STORE['reference_faces'].clear()
