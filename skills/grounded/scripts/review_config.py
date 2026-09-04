"""Canonical review budgets. Generated documentation and evaluations consume these."""
WORD_BUDGETS = {
    "scientific": {"small": (600, 1000), "medium": (1500, 2500), "large": (3500, 6000)},
    "popsci": {"small": (600, 1000), "medium": (1500, 2500), "large": (3500, 6000)},
    "bullets": {"small": (350, 700), "medium": (900, 1600), "large": (2000, 4000)},
    "eli5": {"small": (350, 700), "medium": (900, 1600), "large": (2000, 4000)},
}

TIER_REQUIREMENTS = {
    "small": {"sections": (3, 5), "sources": (10, 20), "tables": (0, 1),
              "fulltexts": (2, None), "figure_target": 2, "figure_cap": 2},
    "medium": {"sections": (6, 9), "sources": (30, 60), "tables": (1, 2),
               "fulltexts": (8, None), "figure_target": 3, "figure_cap": 5},
    "large": {"sections": (10, 15), "sources": (70, 150), "tables": (2, 4),
              "fulltexts": (25, None), "figure_target": 5, "figure_cap": 8},
}

SEARCH_REQUIREMENTS = {
    "small": {"angles": (3, 5), "queries": (1, 2), "central": (0, None)},
    "medium": {"angles": (5, 8), "queries": (2, 3), "central": (0, None)},
    "large": {"angles": (8, 12), "queries": (3, 5), "central": (5, 10)},
}
CLAIM_RANGES = {"small": (5, 12), "medium": (10, 25), "large": (20, 45)}

DECK_BUDGETS = {
    "small": {"content": (4, 6), "total": (6, 8), "reference_min": 1},
    "medium": {"content": (8, 12), "total": (10, 15), "reference_min": 1},
    "large": {"content": (14, 20), "total": (18, 25), "reference_min": 3},
}
