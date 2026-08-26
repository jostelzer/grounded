import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "find_papers.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("find_papers", SCRIPT)
find_papers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(find_papers)


def openalex_work(number, work_type="article", source_type="journal", citations=0):
    return {
        "id": f"https://openalex.org/W{number}",
        "doi": f"https://doi.org/10.1000/{number}",
        "title": f"Study {number}",
        "authorships": [{"author": {"display_name": f"Author {number}"}}],
        "publication_year": 2020 + number,
        "publication_date": f"{2020 + number}-01-01",
        "cited_by_count": citations,
        "primary_location": {
            "source": {"display_name": "Test Journal", "type": source_type},
        },
        "type": work_type,
        "abstract_inverted_index": {"Abstract": [0], str(number): [1]},
        "is_retracted": False,
        "ids": {},
        "best_oa_location": {},
        "open_access": {},
    }


def pubmed_xml(pmids, publication_type="Journal Article"):
    articles = []
    for pmid in pmids:
        articles.append(f"""
        <PubmedArticle>
          <MedlineCitation>
            <PMID>{pmid}</PMID>
            <Article>
              <ArticleTitle>PubMed study {pmid}</ArticleTitle>
              <ELocationID EIdType="doi">10.2000/{pmid}</ELocationID>
              <Journal>
                <Title>Medical Journal</Title>
                <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
              </Journal>
              <AuthorList>
                <Author><LastName>Tester</LastName><ForeName>Ada</ForeName></Author>
              </AuthorList>
              <Abstract><AbstractText>Test abstract.</AbstractText></Abstract>
              <PublicationTypeList><PublicationType>{publication_type}</PublicationType></PublicationTypeList>
            </Article>
          </MedlineCitation>
          <PubmedData>
            <ArticleIdList><ArticleId IdType="pubmed">{pmid}</ArticleId></ArticleIdList>
          </PubmedData>
        </PubmedArticle>
        """)
    return "<PubmedArticleSet>" + "".join(articles) + "</PubmedArticleSet>"


class FakeOpenAlexClient:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.calls = []
        self.unavailable = None
        self.mailto = None
        self.api_key = None

    @property
    def enabled(self):
        return self.unavailable is None

    def add_identity(self, params):
        return dict(params)

    def fetch(self, url, latch=True):
        self.calls.append(url)
        return self.fetcher(url)


class PaginationTests(unittest.TestCase):
    def test_openalex_uses_cursor_pagination_and_respects_total_limit(self):
        pages = {
            "*": {
                "meta": {"count": 4, "next_cursor": "cursor-2"},
                "results": [openalex_work(1), openalex_work(2)],
            },
            "cursor-2": {
                "meta": {"count": 4, "next_cursor": None},
                "results": [openalex_work(3), openalex_work(4)],
            },
        }

        def fetcher(url):
            cursor = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["cursor"][0]
            return json.dumps(pages[cursor])

        client = FakeOpenAlexClient(fetcher)
        result = find_papers.search_openalex(
            client, "sleep", None, None, limit=3, types="all",
            sort="relevance", page_size=2,
        )

        self.assertEqual(result.total_matches, 4)
        self.assertEqual(result.pages, 2)
        self.assertEqual([hit["title"] for hit in result.hits], ["Study 1", "Study 2", "Study 3"])
        cursors = [
            urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["cursor"][0]
            for url in client.calls
        ]
        self.assertEqual(cursors, ["*", "cursor-2"])

    def test_pubmed_uses_retstart_pagination(self):
        starts = []
        sorts = []

        def fake_get(url, *args, **kwargs):
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            if parsed.path.endswith("esearch.fcgi"):
                start = int(params["retstart"][0])
                starts.append(start)
                sorts.append(params["sort"][0])
                ids = ["1", "2"] if start == 0 else ["3"]
                return json.dumps({"esearchresult": {"count": "3", "idlist": ids}})
            ids = params["id"][0].split(",")
            return pubmed_xml(ids)

        with mock.patch.object(find_papers, "get", side_effect=fake_get):
            result = find_papers.search_pubmed(
                "sleep", None, None, limit=3, types="all", page_size=2,
                sort="pub-date",
            )

        self.assertEqual(starts, [0, 2])
        self.assertEqual(sorts, ["pub_date", "pub_date"])
        self.assertEqual(result.total_matches, 3)
        self.assertEqual(result.pages, 2)
        self.assertEqual([hit["pmid"] for hit in result.hits], ["1", "2", "3"])


class QueryAndPolicyTests(unittest.TestCase):
    def test_database_specific_queries_do_not_cross_services(self):
        plan = find_papers.build_query_plan(
            ["shared"], ["openalex syntax"], ['sleep[tiab] AND trial[pt]'],
            ["openalex", "pubmed"],
        )
        self.assertEqual(plan, [
            ("openalex", "shared"),
            ("pubmed", "shared"),
            ("openalex", "openalex syntax"),
            ("pubmed", "sleep[tiab] AND trial[pt]"),
        ])

    def test_strict_policy_rejects_non_evidence_and_marks_candidates_honestly(self):
        journal = find_papers.parse_openalex_work(openalex_work(1))
        repository = find_papers.parse_openalex_work(
            openalex_work(2, source_type="repository")
        )
        conference = find_papers.parse_openalex_work(
            openalex_work(3, work_type="article", source_type="conference")
        )
        editorial = {
            "_source": "pubmed", "journal": "Medical Journal", "is_preprint": False,
            "pub_types": ["Journal Article", "Editorial"],
        }
        untyped = {
            "_source": "pubmed", "journal": "Medical Journal", "is_preprint": False,
            "pub_types": [],
        }

        accepted, excluded = find_papers.filter_candidates(
            [journal, repository, conference, editorial, untyped], policy="strict",
        )
        self.assertEqual(accepted, [journal])
        self.assertEqual(journal["peer_review_status"], "not_independently_verified")
        self.assertEqual(excluded["OpenAlex source type repository"], 1)
        self.assertEqual(excluded["conference paper not enabled"], 1)
        self.assertEqual(excluded["PubMed non-evidence type: Editorial"], 1)
        self.assertEqual(excluded["no eligible PubMed publication type"], 1)

        accepted, _ = find_papers.filter_candidates(
            [conference], include_conference_papers=True, policy="strict",
        )
        self.assertEqual(accepted, [conference])
        self.assertEqual(conference["publication_eligibility"], "conference-paper candidate")


class CitationChasingTests(unittest.TestCase):
    def test_backward_and_forward_chasing_adds_directional_provenance(self):
        seed = openalex_work(0)
        seed["referenced_works"] = [
            "https://openalex.org/W1", "https://openalex.org/W2",
        ]

        def fetcher(url):
            parsed = urllib.parse.urlparse(url)
            if parsed.path.endswith("/W0"):
                return json.dumps(seed)
            params = urllib.parse.parse_qs(parsed.query)
            work_filter = params.get("filter", [""])[0]
            if work_filter.startswith("openalex:"):
                return json.dumps({
                    "meta": {"count": 2, "next_cursor": None},
                    "results": [
                        openalex_work(1, citations=5),
                        openalex_work(2, citations=50),
                    ],
                })
            if work_filter == "cites:W0":
                return json.dumps({
                    "meta": {"count": 1, "next_cursor": None},
                    "results": [openalex_work(3, citations=7)],
                })
            raise AssertionError(f"unexpected URL: {url}")

        client = FakeOpenAlexClient(fetcher)
        ledger = {"entries": [{"key": "Seed2020study", "openalex": "https://openalex.org/W0"}]}
        results = find_papers.chase_citations(
            client, ledger, ["Seed2020study"], direction="both",
            limit=2, pool=10, page_size=2, chase_sort="cited",
        )

        self.assertEqual(len(results), 2)
        self.assertEqual([hit["openalex"] for hit in results[0].hits], [
            "https://openalex.org/W2", "https://openalex.org/W1",
        ])
        self.assertEqual(results[0].hits[0]["_citation_direction"], "backward")
        self.assertEqual(results[1].hits[0]["_citation_direction"], "forward")

        accepted, _ = find_papers.filter_candidates(results[0].hits)
        target_ledger = {"created": "2026-01-01", "entries": []}
        find_papers.merge(
            target_ledger, accepted, results[0].query, "foundations",
            method="backward-citation",
        )
        provenance = target_ledger["entries"][0]["found_by"][0]
        self.assertEqual(provenance["direction"], "backward")
        self.assertEqual(provenance["seed"], "Seed2020study")


class LoggingAndIntegrationTests(unittest.TestCase):
    def test_log_is_created_automatically_beside_ledger(self):
        hit = find_papers.parse_pubmed_articles(pubmed_xml(["42"]))[0]
        result = find_papers.SearchResult(
            database="pubmed", query="sleep", api_query="sleep[tiab]",
            filters="none", sort="relevance", hits=[hit],
            total_matches=12, pages=1,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "sources.json"
            with mock.patch.object(find_papers, "search_pubmed", return_value=result):
                with contextlib.redirect_stdout(io.StringIO()):
                    exit_code = find_papers.main([
                        "--sources", "pubmed", "--pubmed-query", "sleep[tiab]",
                        "--ledger", str(ledger_path), "--limit", "1",
                    ])

            log_path = Path(temp_dir) / "search_log.md"
            self.assertEqual(exit_code, 0)
            self.assertTrue(log_path.exists())
            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn("| pubmed | keyword |", log_text)
            self.assertIn("sleep[tiab]", log_text)
            self.assertIn("| 12 | 1 | 1 | 1 | 0 | 1 |", log_text)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(len(ledger["entries"]), 1)
            self.assertEqual(
                ledger["entries"][0]["peer_review_status"],
                "not_independently_verified",
            )


if __name__ == "__main__":
    unittest.main()
