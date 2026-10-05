"""Canonical review budgets. Generated documentation and evaluations consume these."""
WORD_BUDGETS = {
    "scientific": {"small": (600, 1000), "medium": (1500, 2500), "large": (3500, 6000)},
    "popsci": {"small": (650, 1300), "medium": (1800, 3000), "large": (4000, 7000)},
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

# A popular-science feature tells a handful of studies as small stories and needs
# room for mechanism, yardsticks and methods in plain words: fewer, fuller sections,
# more words than a scientific review of the same size, fewer cited sources than
# the ledger holds. Other styles use the tier's ranges.
STYLE_SECTIONS = {"popsci": {"small": (2, 4), "medium": (4, 7), "large": (6, 10)}}
STYLE_SOURCES = {"popsci": {"small": (6, 15), "medium": (12, 35), "large": (25, 60)}}
# Writers given only a range drift to its ends; the target sits near the middle.
POPSCI_TARGET_WORDS = {"small": 1000, "medium": 2400, "large": 5500}


def section_range(style, size):
    return STYLE_SECTIONS.get(style, {}).get(size, TIER_REQUIREMENTS[size]["sections"])


def source_range(style, size):
    return STYLE_SOURCES.get(style, {}).get(size, TIER_REQUIREMENTS[size]["sources"])

SEARCH_REQUIREMENTS = {
    "small": {"angles": (3, 5), "queries": (1, 2), "central": (0, None)},
    "medium": {"angles": (5, 8), "queries": (2, 3), "central": (0, None)},
    "large": {"angles": (8, 12), "queries": (3, 5), "central": (5, 10)},
}
CLAIM_RANGES = {"small": (5, 12), "medium": (10, 25), "large": (20, 45)}
# Popsci readability guide for readability_profile.py: upper bounds, set from
# Grounded drafts that cold readers found easy or hard and from published features.
# They are questions for the writer, never release gates; a topic that is about
# quantities will carry more numbers than one that is not.
READABILITY_GUIDE = {
    "numbers_per_100_words": 4.0,
    "numeric_paragraph_share": 0.75,
    "statistics_terms_per_1000_words": 2.0,
    "sources_per_1000_words": 12.0,
    "study_roll_calls_per_1000_words": 4.0,
    "mean_sentence_words": 24.0,
    "mean_paragraph_words": 110.0,
    "short_paragraph_share": 0.25,
    "reading_grade": 12.5,
    "hedges_per_1000_words": 3.0,
    "negations_per_1000_words": 4.0,
    # passage-level limits, and how many such passages may remain
    "long_sentence_words": 42,
    "numbers_per_sentence": 3,
    "numbers_per_paragraph": 6,
    "long_paragraph_words": 160,
    "sources_per_paragraph": 3,
    "max_long_sentences": 3,
    "max_number_heavy_sentences": 3,
    "max_number_heavy_paragraphs": 2,
    "max_long_paragraphs": 1,
    "max_source_heavy_paragraphs": 2,
    "max_self_reference": 0,
    "max_caveat_closers": 3,
}

# Popsci working steps: the reader questions the article must answer and the
# story notes (verified facts on methods, terms, mechanisms and scale). Advisory.
FACT_RANGES = {"small": (10, 30), "medium": (20, 60), "large": (40, 100)}
QUESTION_RANGES = {"small": (6, 10), "medium": (8, 12), "large": (10, 16)}

DECK_BUDGETS = {
    "small": {"content": (4, 6), "total": (6, 8), "reference_min": 1},
    "medium": {"content": (8, 12), "total": (10, 15), "reference_min": 1},
    "large": {"content": (14, 20), "total": (18, 25), "reference_min": 3},
}
