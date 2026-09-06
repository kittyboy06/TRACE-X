import io
import json
import os
import zipfile
from pathlib import Path
from typing import Dict, Any, List

from app.services.collectors.base_collector import BaseCollector

MAX_INPUT_SIZE = 10 * 1024 * 1024       # 10 MB compressed input limit
MAX_ZIP_ENTRIES = 50                    # 50 ZIP entries limit
MAX_UNCOMPRESSED = 25 * 1024 * 1024     # 25 MB max uncompressed limit
MAX_COMPRESSION_RATIO = 100             # Secondary ratio heuristic


class ManualUploadCollector(BaseCollector):
    """
    Collector handling manual JSON and ZIP archive evidence package uploads.
    Enforces strict security boundaries against zip bombs, directory traversal,
    and corrupted archives.
    """

    def collect(self, source_descriptor: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses evidence from provided bytes or dictionary payload.
        source_descriptor:
        {
            "format": "json" | "zip",
            "content": bytes | str | dict,
            "filename": Optional[str]
        }
        """
        upload_format = source_descriptor.get("format", "json").lower()
        content = source_descriptor.get("content")

        if upload_format == "json":
            return self._parse_json(content)
        elif upload_format == "zip":
            return self._parse_zip(content)
        else:
            raise ValueError(f"Unsupported evidence package format '{upload_format}'. Allowed: json, zip")

    def _parse_json(self, content: Any) -> Dict[str, Any]:
        if isinstance(content, dict):
            data = content
        elif isinstance(content, (bytes, bytearray)):
            if len(content) > MAX_INPUT_SIZE:
                raise ValueError(f"JSON upload exceeds max limit of {MAX_INPUT_SIZE // (1024 * 1024)} MB.")
            data = json.loads(content.decode("utf-8"))
        elif isinstance(content, str):
            if len(content.encode("utf-8")) > MAX_INPUT_SIZE:
                raise ValueError(f"JSON upload exceeds max limit of {MAX_INPUT_SIZE // (1024 * 1024)} MB.")
            data = json.loads(content)
        else:
            raise ValueError("Invalid content type for JSON evidence package.")

        self._validate_package_structure(data)
        return data

    def _parse_zip(self, content: Any) -> Dict[str, Any]:
        if not isinstance(content, (bytes, bytearray)):
            raise ValueError("ZIP content must be provided as bytes.")

        # Guard 1: Compressed Input Size
        if len(content) > MAX_INPUT_SIZE:
            raise ValueError(f"Archive exceeds maximum allowed size of {MAX_INPUT_SIZE // (1024 * 1024)} MB.")

        try:
            zip_buffer = io.BytesIO(content)
            with zipfile.ZipFile(zip_buffer, "r") as zf:
                infolist = zf.infolist()

                # Guard 2: Entry Count Limit
                if len(infolist) > MAX_ZIP_ENTRIES:
                    raise ValueError(f"Archive contains {len(infolist)} entries, exceeding maximum allowed of {MAX_ZIP_ENTRIES}.")

                total_uncompressed = 0
                extracted_artifacts: List[Dict[str, Any]] = []
                package_meta: Dict[str, Any] = {}

                for info in infolist:
                    # Guard 3: Directory Traversal Prevention
                    filename = info.filename
                    if filename.startswith("/") or filename.startswith("\\") or ".." in filename.split("/") or ".." in filename.split("\\"):
                        raise ValueError(f"Illegal path traversal sequence detected in archive entry: '{filename}'.")

                    # Guard 4: Total Uncompressed Size Limit
                    total_uncompressed += info.file_size
                    if total_uncompressed > MAX_UNCOMPRESSED:
                        raise ValueError(f"Decompressed archive size exceeds maximum limit of {MAX_UNCOMPRESSED // (1024 * 1024)} MB.")

                    # Guard 5: Compression Ratio Heuristic
                    if info.compress_size > 0:
                        ratio = info.file_size / info.compress_size
                        if ratio > MAX_COMPRESSION_RATIO:
                            raise ValueError(f"Suspicious compression ratio ({ratio:.1f}x) in entry '{filename}'. Possible zip bomb.")

                    if info.is_dir():
                        continue

                    # Read and process JSON files
                    if filename.lower().endswith(".json"):
                        file_data = zf.read(info)
                        try:
                            parsed = json.loads(file_data.decode("utf-8"))
                            # If file represents a full package
                            if "artifacts" in parsed and isinstance(parsed["artifacts"], list):
                                if not package_meta:
                                    package_meta = {
                                        "investigation_id": parsed.get("investigation_id"),
                                        "title": parsed.get("title"),
                                        "target_persona_a": parsed.get("target_persona_a"),
                                        "target_persona_b": parsed.get("target_persona_b"),
                                        "narrative": parsed.get("narrative")
                                    }
                                extracted_artifacts.extend(parsed["artifacts"])
                            elif "raw_payload" in parsed:
                                # Individual artifact file
                                extracted_artifacts.append(parsed)
                        except Exception as e:
                            raise ValueError(f"Failed to parse JSON in entry '{filename}': {str(e)}")

                if not extracted_artifacts:
                    raise ValueError("Archive contains no valid JSON evidence artifacts.")

                result = {
                    "investigation_id": package_meta.get("investigation_id") or "INV-UPLOAD-ARCHIVE",
                    "title": package_meta.get("title") or "Ingested Archive Evidence",
                    "target_persona_a": package_meta.get("target_persona_a") or "Persona_A",
                    "target_persona_b": package_meta.get("target_persona_b") or "Persona_B",
                    "narrative": package_meta.get("narrative") or "Archive ingestion",
                    "artifacts": extracted_artifacts
                }
                return result

        except zipfile.BadZipFile:
            raise ValueError("Uploaded file is not a valid or intact ZIP archive.")

    def _validate_package_structure(self, data: Dict[str, Any]):
        required = ["investigation_id", "target_persona_a", "target_persona_b", "artifacts"]
        for field in required:
            if field not in data:
                raise ValueError(f"Evidence package missing required field '{field}'.")
        if not isinstance(data["artifacts"], list) or len(data["artifacts"]) == 0:
            raise ValueError("Evidence package must contain a non-empty 'artifacts' list.")
