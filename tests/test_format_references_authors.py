"""Institution-shaped Crossref author records must never lead a citation.

Some Crossref records interleave affiliations or group names into the author
array (e.g. 10.15605/jafes.037.02.14, whose first "author" is "Department of
Medicine, St. Luke's Medical Center, Quezon City, Philippines"). The in-text
tag and the alphabetical sort must use the first person; the reference list
drops affiliation-shaped records while keeping genuine group authors.
"""
import importlib.util
import os
import unittest

ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "grounded",
)
SCRIPT = os.path.join(ROOT, "scripts", "format_references.py")
SPEC = importlib.util.spec_from_file_location("format_references", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

AFFILIATION = ("Department of Medicine, St. Luke’s Medical Center, "
               "Quezon City, Philippines")
SECTION = ("Section of Endocrinology, Diabetes and Metabolism, Department of "
           "Medicine, St. Luke’s Medical Center, Quezon City, Philippines")


def canonical(authors, year=2022):
    return {"authors_structured": authors, "year": year, "title": "A Study.",
            "journal": "Journal"}


ST_LUKES = [
    {"family": AFFILIATION, "given": ""},
    {"family": "Tan", "given": "HC"},
    {"family": "Dampil", "given": "OA"},
    {"family": SECTION, "given": ""},
    {"family": "Marquez", "given": "MM"},
]


class PersonDetectionTests(unittest.TestCase):
    def test_affiliation_records_are_not_people(self):
        for family in (AFFILIATION, SECTION, "STEP 4 Investigators",
                       "CONSORT Group", ""):
            with self.subTest(family=family):
                self.assertFalse(MODULE.is_person({"family": family, "given": ""}))

    def test_people_are_people_with_or_without_given_names(self):
        for author in ({"family": "Tan", "given": "HC"},
                       {"family": "Smith", "given": ""},
                       {"family": "van der Berg", "given": "J"}):
            with self.subTest(author=author):
                self.assertTrue(MODULE.is_person(author))


class InTextTagTests(unittest.TestCase):
    def test_first_person_leads_the_bracket_tag(self):
        self.assertEqual(MODULE.bracket_intext(canonical(ST_LUKES)),
                         "Tan et al. 2022")

    def test_two_people_plus_junk_render_as_a_pair(self):
        authors = [{"family": AFFILIATION, "given": ""},
                   {"family": "Tan", "given": "HC"},
                   {"family": "Dampil", "given": "OA"}]
        self.assertEqual(MODULE.bracket_intext(canonical(authors)),
                         "Tan & Dampil 2022")

    def test_apa_tag_uses_the_first_person_too(self):
        self.assertEqual(MODULE.apa_intext(canonical(ST_LUKES)),
                         "Tan et al., 2022")

    def test_corporate_only_author_lists_still_render(self):
        authors = [{"family": "CONSORT Group", "given": ""}]
        self.assertEqual(MODULE.bracket_intext(canonical(authors, 2010)),
                         "CONSORT Group 2010")

    def test_sorting_uses_the_first_person_surname(self):
        self.assertEqual(MODULE.lead_family(canonical(ST_LUKES)), "tan")


class ReferenceListTests(unittest.TestCase):
    def test_affiliations_are_dropped_from_the_sources_line(self):
        line = MODULE.fmt_bracket(canonical(ST_LUKES), "10.15605/jafes.037.02.14")
        self.assertIn("Tan H, Dampil O, Marquez M (2022)", line)
        self.assertNotIn("Department of Medicine", line)
        self.assertNotIn("Section of Endocrinology", line)

    def test_genuine_group_authors_stay_listed(self):
        authors = [{"family": "Rubino", "given": "D"},
                   {"family": "STEP 4 Investigators", "given": ""},
                   {"family": "Wadden", "given": "TA"}]
        line = MODULE.fmt_bracket(canonical(authors, 2021), "10.1001/jama.2021.3224")
        self.assertIn("STEP 4 Investigators", line)
        self.assertEqual(MODULE.bracket_intext(canonical(authors, 2021)),
                         "Rubino & Wadden 2021")


if __name__ == "__main__":
    unittest.main()
