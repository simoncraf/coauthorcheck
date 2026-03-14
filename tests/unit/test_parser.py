import unittest

from coauthorcheck.parser import extract_coauthor_trailers, extract_trailer_block


class TrailerParserTests(unittest.TestCase):
    def test_non_trailer_footer_is_not_treated_as_trailer_block(self) -> None:
        message = (
            "Subject\n\n"
            "Body line\n\n"
            "This is just a closing sentence.\n"
        )

        self.assertEqual(extract_trailer_block(message), [])

    def test_extracts_only_trailing_trailer_block(self) -> None:
        message = (
            "Subject\n\n"
            "Body line\n"
            "Co-authored-by: Ignored Person <ignored@example.com>\n\n"
            "Signed-off-by: Main Author <main@example.com>\n"
            "Co-authored-by: Jane Doe <jane@example.com>\n"
        )

        block = extract_trailer_block(message)

        self.assertEqual(
            block,
            [
                (6, "Signed-off-by: Main Author <main@example.com>"),
                (7, "Co-authored-by: Jane Doe <jane@example.com>"),
            ],
        )

    def test_detects_coauthor_case_insensitively(self) -> None:
        message = (
            "Subject\n\n"
            "co-authored-by: Jane Doe <jane@example.com>\n"
            "CO-AUTHORED-BY: John Doe <john@example.com>\n"
        )

        trailers = extract_coauthor_trailers(message)

        self.assertEqual([trailer.token for trailer in trailers], ["co-authored-by", "CO-AUTHORED-BY"])


if __name__ == "__main__":
    unittest.main()
