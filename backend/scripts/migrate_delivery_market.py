from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

import json

from datetime import datetime

from sqlalchemy import select

from sqlalchemy.orm import Session

from app.core.db import (
    Base,
    engine,
)

import app.models  # noqa: F401

from app.models import (
    PricingModelVersion,
)

from app.services.upfront_delivery import (
    DEFAULT_COEFFICIENTS,
)


Base.metadata.create_all(
    bind=engine
)


with Session(
    engine
) as db:

    active = db.scalars(
        select(
            PricingModelVersion
        )
        .where(
            PricingModelVersion.status
            == "active"
        )
    ).first()


    if not active:

        active = PricingModelVersion(
            version_name=(
                "storedash-market-v1-public-bootstrap"
            ),

            status=
                "active",

            source=(
                "public-market-bootstrap"
            ),

            coefficients_json=
                json.dumps(
                    DEFAULT_COEFFICIENTS
                ),

            metrics_json=
                json.dumps(
                    {
                        "note":
                            "Bootstrap model. "
                            "CargoMov live bids "
                            "must override uncertainty.",

                        "public_anchors_ghs": {
                            "mini_van":
                                120,

                            "van":
                                160,

                            "pickup":
                                220,

                            "kia_truck":
                                320,

                            "truck_16ft":
                                650,

                            "truck_20ft":
                                1300,
                        },
                    }
                ),

            activated_at=
                datetime.utcnow(),
        )


        db.add(
            active
        )

        db.commit()

        print(
            "Seeded initial active "
            "StoreDash pricing model."
        )

    else:

        print(
            "Active model already exists:",
            active.version_name,
        )


print(
    "Delivery-market migration complete."
)
