"""Synthetic checks for spatial review transformations and decision ownership."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_spatial_selection_review import (  # noqa: E402
    RELATIONS,
    build_decision_template,
    standardized_estimate,
)


def test_standardized_estimate_scales_beta_and_standard_error():
    beta, standard_error = standardized_estimate(
        beta=2.0,
        standard_error=0.5,
        sd_x=3.0,
        sd_y=2.0,
    )

    assert beta == 3.0
    assert standard_error == 0.75


def test_decision_template_does_not_auto_select_models():
    rows = []
    for specification, outcome, label, role in RELATIONS:
        for weight in ("queen_contiguity", "symmetric_knn5"):
            rows.append(
                {
                    "specification": specification,
                    "outcome": outcome,
                    "relationship": label,
                    "role": role,
                    "weight": weight,
                    "model": "OLS",
                    "bic": 10.0,
                    "n_fit": 100,
                }
            )
    template = build_decision_template(pd.DataFrame(rows))

    assert len(template) == 9
    assert template["final_model_decision"].isna().all()
    assert template["final_weight_decision"].isna().all()
    assert template["status"].eq("Pending researcher choice").all()
