from pathlib import Path
import sys

ROOT = Path(
    __file__
).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from app.core.db import (
    Base,
    engine,
)

import app.models  # noqa: F401


Base.metadata.create_all(
    bind=engine
)

print(
    "StoreDash batching-system migration complete."
)
