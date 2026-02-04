import unittest
from unittest.mock import MagicMock
import sys

# Mock dependencies before imports to ensure test runs even if deps are missing in environment
sys.modules['insightface'] = MagicMock()
sys.modules['mediapipe'] = MagicMock()
sys.modules['onnxruntime'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['cv2.typing'] = MagicMock()
sys.modules['psutil'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['torchvision'] = MagicMock()

import gradio
from watserface import state_manager
from watserface.uis.components import output, source, target

class TestUIUX(unittest.TestCase):
    def setUp(self):
        # Mock state_manager.get_item to return None to avoid side effects
        self.original_get_item = state_manager.get_item
        state_manager.get_item = MagicMock(return_value=None)

    def tearDown(self):
        state_manager.get_item = self.original_get_item

    def test_output_path_info(self):
        output.render()
        self.assertIsNotNone(output.OUTPUT_PATH_TEXTBOX.info)
        self.assertEqual(output.OUTPUT_PATH_TEXTBOX.info, 'specify the image or video within a directory')

    def test_components_render_without_error(self):
        # Regression test to ensure rendering works
        source.render()
        target.render()
        # Source/Target don't support info yet, but ensuring they render is good
        self.assertIsInstance(source.SOURCE_FILE, gradio.File)
        self.assertIsInstance(target.TARGET_FILE, gradio.File)

if __name__ == '__main__':
    unittest.main()
