__all__ = ["bind_runtime"]


def bind_runtime(*args, **kwargs):
    from ocr4game.runtime.binding import bind_runtime as _bind_runtime

    return _bind_runtime(*args, **kwargs)
