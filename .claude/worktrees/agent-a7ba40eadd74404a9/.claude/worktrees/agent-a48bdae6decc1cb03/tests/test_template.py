from pathlib import Path

import cv2
import numpy as np

from ocr4game.perception.template import TemplateMatcher


def test_template_match_self(tmp_path: Path):
    img = np.zeros((80, 120, 3), dtype=np.uint8)
    cv2.rectangle(img, (30, 20), (70, 50), (255, 255, 255), -1)
    tpl_path = tmp_path / "btn.png"
    tpl = img[18:52, 28:72].copy()
    cv2.imwrite(str(tpl_path), tpl)

    matcher = TemplateMatcher()
    result = matcher.match(img, tpl_path, threshold=0.9)
    assert result.found
    assert result.confidence >= 0.9
