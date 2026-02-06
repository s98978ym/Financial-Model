"""Generate multiple case variants (Best/Base/Worst) from parameters."""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from copy import deepcopy

from ..config.models import ExtractedParameter, PhaseAConfig

logger = logging.getLogger(__name__)

# Default case adjustment rules
CASE_RULES = {
    "best": {
        "revenue_multiplier": 1.2,  # Revenue +20%
        "cost_multiplier": 0.9,     # Costs -10%
        "growth_multiplier": 1.3,   # Growth rates +30%
        "churn_multiplier": 0.7,    # Churn -30%
    },
    "base": {
        "revenue_multiplier": 1.0,
        "cost_multiplier": 1.0,
        "growth_multiplier": 1.0,
        "churn_multiplier": 1.0,
    },
    "worst": {
        "revenue_multiplier": 0.8,  # Revenue -20%
        "cost_multiplier": 1.15,    # Costs +15%
        "growth_multiplier": 0.7,   # Growth rates -30%
        "churn_multiplier": 1.5,    # Churn +50%
    },
}

# Keywords to classify parameters
REVENUE_KEYWORDS = ["revenue", "売上", "arpu", "price", "単価", "gmv", "arr", "mrr"]
COST_KEYWORDS = ["cost", "費", "expense", "コスト", "原価", "人件費", "家賃"]
GROWTH_KEYWORDS = ["growth", "成長", "増加", "伸び"]
CHURN_KEYWORDS = ["churn", "解約", "離脱", "退会"]


class CaseGenerator:
    """Generates Best/Base/Worst case parameter sets."""

    def __init__(self, config: PhaseAConfig):
        self.config = config

    def generate_cases(
        self, base_parameters: List[ExtractedParameter]
    ) -> Dict[str, List[ExtractedParameter]]:
        """
        Generate parameter sets for each requested case.

        If separate templates exist for each case, parameters are used as-is.
        Otherwise, derive from base using CASE_RULES.
        """
        cases = {}

        for case_name in self.config.cases:
            if case_name == "base":
                cases["base"] = deepcopy(base_parameters)
            else:
                cases[case_name] = self._derive_case(base_parameters, case_name)

        return cases

    def _derive_case(
        self, base_params: List[ExtractedParameter], case_name: str
    ) -> List[ExtractedParameter]:
        """Derive a case variant from base parameters using rules."""
        rules = CASE_RULES.get(case_name, CASE_RULES["base"])
        derived = []

        for param in base_params:
            new_param = deepcopy(param)

            if isinstance(param.value, (int, float)):
                multiplier = self._get_multiplier(param.key, param.label, rules)
                new_param.value = round(param.value * multiplier, 2)
                if new_param.adjusted_value is not None:
                    new_param.adjusted_value = round(new_param.adjusted_value * multiplier, 2)

            derived.append(new_param)

        return derived

    def _get_multiplier(self, key: str, label: str, rules: dict) -> float:
        """Determine which multiplier to apply based on parameter classification."""
        combined = f"{key} {label}".lower()

        if any(kw in combined for kw in CHURN_KEYWORDS):
            return rules["churn_multiplier"]
        if any(kw in combined for kw in GROWTH_KEYWORDS):
            return rules["growth_multiplier"]
        if any(kw in combined for kw in REVENUE_KEYWORDS):
            return rules["revenue_multiplier"]
        if any(kw in combined for kw in COST_KEYWORDS):
            return rules["cost_multiplier"]

        return 1.0  # No adjustment for unclassified params

    def get_case_diff_report(
        self, cases: Dict[str, List[ExtractedParameter]]
    ) -> str:
        """Generate a diff report comparing parameter values across cases."""
        if len(cases) < 2:
            return "Only one case generated, no diff available."

        lines = ["# Case Comparison Report\n"]
        lines.append("| Parameter | " + " | ".join(cases.keys()) + " |")
        lines.append("|" + "---|" * (len(cases) + 1))

        # Collect all parameter keys
        all_keys = set()
        for params in cases.values():
            for p in params:
                all_keys.add(p.key)

        for key in sorted(all_keys):
            row = [key]
            for case_name, params in cases.items():
                param = next((p for p in params if p.key == key), None)
                if param:
                    val = param.adjusted_value if param.adjusted_value is not None else param.value
                    row.append(str(val))
                else:
                    row.append("-")
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)
