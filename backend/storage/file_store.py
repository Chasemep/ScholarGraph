"""Local PDF file storage repository manager for persisting and serving binary documents."""

import re
import shutil
from pathlib import Path
from typing import List, Optional

from backend.config import PROJECT_ROOT, settings


PDF_MAGIC_BYTES = b"%PDF-"


class FileStoreManager:
    """Manages local filesystem persistence and validation for scientific PDFs."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir).resolve() if base_dir else Path(settings.papers_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize an uploaded filename to prevent path traversal and invalid characters."""
        name = Path(filename).name.strip()
        sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        if not sanitized.lower().endswith(".pdf"):
            sanitized += ".pdf"
        return sanitized

    @staticmethod
    def validate_pdf_bytes(content: bytes) -> bool:
        """Verify that binary content starts with the PDF magic header (%PDF-)."""
        return bool(content and len(content) >= 5 and content[:5] == PDF_MAGIC_BYTES)

    def save_pdf_bytes(self, filename: str, content: bytes) -> Path:
        """Validate and persist raw PDF binary bytes into the papers storage directory."""
        if not self.validate_pdf_bytes(content):
            raise ValueError(f"Invalid PDF binary header for file '{filename}'")
        safe_name = self.sanitize_filename(filename)
        dest_path = (self.base_dir / safe_name).resolve()
        if not str(dest_path).startswith(str(self.base_dir)):
            raise ValueError("Path traversal detected in filename")
        dest_path.write_bytes(content)
        return dest_path

    def copy_pdf_file(self, source_path: Path, target_filename: Optional[str] = None) -> Path:
        """Copy an existing PDF file from disk into the papers storage directory."""
        src = Path(source_path).resolve()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Source PDF file not found: {src}")
        with src.open("rb") as f:
            header = f.read(5)
        if header != PDF_MAGIC_BYTES:
            raise ValueError(f"File '{src.name}' is not a valid PDF document")

        safe_name = self.sanitize_filename(target_filename or src.name)
        dest_path = (self.base_dir / safe_name).resolve()
        if src != dest_path:
            shutil.copy2(src, dest_path)
        return dest_path

    def resolve_pdf_path(self, filepath_or_name: str) -> Path:
        """Resolve a stored relative filepath or filename to an existing absolute Path."""
        candidate = Path(filepath_or_name)
        if not candidate.is_absolute():
            # Check relative to PROJECT_ROOT first, then relative to base_dir
            root_candidate = (PROJECT_ROOT / candidate).resolve()
            if root_candidate.exists() and root_candidate.is_file():
                return root_candidate
            base_candidate = (self.base_dir / candidate.name).resolve()
            if base_candidate.exists() and base_candidate.is_file():
                return base_candidate
        else:
            resolved = candidate.resolve()
            if resolved.exists() and resolved.is_file():
                return resolved

        raise FileNotFoundError(f"PDF file '{filepath_or_name}' not found in storage")

    def get_relative_filepath(self, full_path: Path) -> str:
        """Return POSIX-style path relative to PROJECT_ROOT when possible."""
        resolved = Path(full_path).resolve()
        try:
            return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
        except ValueError:
            return resolved.as_posix()

    def list_stored_pdfs(self) -> List[Path]:
        """List all .pdf files currently stored in the papers directory."""
        return sorted(self.base_dir.glob("*.pdf"))

    def delete_pdf(self, filepath_or_name: str) -> bool:
        """Delete a PDF file from storage if it exists."""
        try:
            target = self.resolve_pdf_path(filepath_or_name)
            target.unlink()
            return True
        except FileNotFoundError:
            return False


file_store = FileStoreManager()

