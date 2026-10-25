from pathlib import Path
import sys

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(
    PROJECT_ROOT
) not in sys.path:
    sys.path.insert(
        0,
        str(
            PROJECT_ROOT
        ),
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
    "StoreDash route-system migration complete."
)
