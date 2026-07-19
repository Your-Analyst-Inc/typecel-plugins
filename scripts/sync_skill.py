#!/usr/bin/env python3
"""Sync the typecel-modeling skill from the production host's public skill endpoint.

The Typecel host bakes the skill into its binary and serves it anonymously at
GET /skills/{name}.zip, so the production zip is the ground truth for the skill content
deployed hosts accept. This script re-publishes that content here with a marketplace
distribution stamp. It no-ops while the production host does not yet serve the skill
under this name, and whenever the content is unchanged (compared by the content hash
recorded in the existing stamp).

Stamp contract (shared with the host's zip stamp): the skill hash is the first 12 hex
characters of sha256 over the SKILL.md content with every carriage return removed and
trailing newlines stripped.
"""

import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

HOST = "https://app.typecel.io/api"
# The production edge rejects the default Python-urllib user agent.
UA = {"User-Agent": "typecel-plugins-sync/1.0"}
NAME = "typecel-modeling"
DEST = Path("plugins/typecel-modeling/skills/typecel-modeling/SKILL.md")
HOST_STAMP = re.compile(r"\n*<!-- distributed by Typecel host [^\n]* -->\n*\Z")
MARKET_STAMP_HASH = re.compile(r"skill sha256:([0-9a-f]{6,64})")


def canonical(content: str) -> str:
    return content.replace("\r", "").rstrip("\n")


def main() -> int:
    index = json.load(urlopen(Request(f"{HOST}/skills", headers=UA), timeout=30))
    entry = next((s for s in index if s.get("name") == NAME), None)
    if entry is None:
        served = [s.get("name") for s in index]
        print(f"host does not serve {NAME} yet (serves: {served}); nothing to sync")
        return 0

    zip_bytes = urlopen(Request(f"{HOST}/skills/{NAME}.zip", headers=UA), timeout=60).read()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        delivered = archive.read(f"{NAME}/SKILL.md").decode("utf-8")

    content = canonical(HOST_STAMP.sub("", delivered))
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]

    existing = DEST.read_text(encoding="utf-8") if DEST.exists() else ""
    recorded = MARKET_STAMP_HASH.search(existing)
    if recorded and recorded.group(1) == digest:
        print(f"already current (skill sha256:{digest})")
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stamp = (
        f"<!-- distributed by Typecel plugin marketplace - {today}Z - channel marketplace"
        f" - skill sha256:{digest} | pass this whole comment as skill_stamp on your first"
        " methodology() call so the host can flag a stale copy -->"
    )
    DEST.write_text(f"{content}\n\n{stamp}\n", encoding="utf-8")
    print(
        f"updated to host {entry.get('hostVersion')} schema v{entry.get('schemaVersion')}"
        f" (skill sha256:{digest})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
