from typing import Dict, ClassVar, Union, IO, Tuple, Optional
from pathlib import Path

MIME: Dict[str, str]

NEAREST: int
BILINEAR: int
BICUBIC: int
LANCZOS: int
ANTIALIAS: int

class Image:
    format: str
    size: Tuple[int, int]

    def resize(self, size: Tuple[int, int], resample: int = 0) -> Image:
        ...
    
    def _getexif(self) -> dict:
        ...

    def save(self, fp: Union[str, Path, IO[bytes]], format: Optional[str] = None) -> None:
        ...

def open(fp: Union[str, Path, IO[bytes]], mode: str = "r") -> Image:
    ...
