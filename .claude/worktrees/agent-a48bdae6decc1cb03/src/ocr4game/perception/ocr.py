"""RapidOCR 封装。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ocr4game.perception.roi import crop_roi


@dataclass
class OcrHit:
    text: str
    confidence: float
    center: tuple[int, int]


class OcrEngine:
    def __init__(self) -> None:
        self._engine = None

    def _lazy_init(self) -> None:
        if self._engine is not None:
            return
        from rapidocr_onnxruntime import RapidOCR

        self._engine = RapidOCR()

    def read(self, frame: np.ndarray, *, roi: list[float] | None = None) -> list[OcrHit]:
        self._lazy_init()
        img = crop_roi(frame, roi) if roi else frame
        ox = int(roi[0] * frame.shape[1]) if roi else 0
        oy = int(roi[1] * frame.shape[0]) if roi else 0

        result, _ = self._engine(img)
        if not result:
            return []

        hits: list[OcrHit] = []
        for box, text, conf in result:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            cx = int(sum(xs) / len(xs)) + ox
            cy = int(sum(ys) / len(ys)) + oy
            hits.append(OcrHit(text=str(text), confidence=float(conf), center=(cx, cy)))
        return hits

    def find_text(
        self,
        frame: np.ndarray,
        expect: list[str],
        *,
        roi: list[float] | None = None,
        min_confidence: float = 0.5,
    ) -> OcrHit | None:
        for hit in self.read(frame, roi=roi):
            if hit.confidence < min_confidence:
                continue
            for kw in expect:
                if kw in hit.text:
                    return hit
        return None
