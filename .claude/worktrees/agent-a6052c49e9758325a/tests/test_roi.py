import numpy as np

from ocr4game.perception.roi import crop_roi, relative_roi_to_pixels


def test_relative_roi_to_pixels():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    x0, y0, x1, y1 = relative_roi_to_pixels(frame, [0.0, 0.0, 0.5, 0.5])
    assert (x0, y0, x1, y1) == (0, 0, 100, 50)


def test_crop_roi_shape():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    crop = crop_roi(frame, [0.25, 0.25, 0.75, 0.75])
    assert crop.shape == (50, 100, 3)
