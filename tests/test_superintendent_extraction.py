"""
Data-driven tests for superintendent extraction.

These tests use real inputs/outputs from actual district websites to ensure
the LLM prompts continue to work correctly after changes.

Test data format:
- input: The parsed HTML text that goes to the LLM
- district_name: The district name for context
- expected_output: What the LLM should return
"""

import pytest
from services.extraction import extract_superintendent


# Test cases extracted from debug_logs with real data
EXTRACTION_TEST_CASES = [
    {
        "id": "adams_board_page_empty",
        "description": "Board page with no superintendent info - should return empty",
        "district_name": "Adams Township School District",
        "input_text": """## Board of Education Board Members  Darren Niemi President Justin Marier Vice
President  Eric Mattila Treasurer Kristen Archambeau Secretary  Trustees: George Eakin Tyler Kinnunen Ashley Sudderth
ADAMS TOWNSHIP SCHOOL DISTRICT MISSION STATEMENT:  To provide a safe environment in which all students
will develop the academic and personal skills necessary to function as responsible citizens in a changing world.""",
        "expected": {
            "is_empty": True,
            "name": None,
            "title": None,
            "email": None,
            "phone": None,
        },
        "reasoning_should_mention": ["board", "no superintendent"]
    },
    {
        "id": "adrian_404_page",
        "description": "404 error page - should return empty",
        "district_name": "Adrian Public Schools",
        "input_text": "## File not found (404 error) If you think what you're looking for should be here, please contact the site owner.",
        "expected": {
            "is_empty": True,
            "name": None,
            "title": None,
            "email": None,
            "phone": None,
        },
        "reasoning_should_mention": ["empty", "404", "no content"]
    },
    # Add more test cases as we collect good/bad examples
]

URL_FILTERING_TEST_CASES = [
    {
        "id": "adams_url_filtering",
        "description": "URL filtering should prioritize contact and board pages",
        "district_name": "Adams Township School District",
        "all_urls": [
            "https://adams.k12.mi.us/district-history.php",
            "https://adams.k12.mi.us",
            "https://adams.k12.mi.us/calendar.php",  # Should be filtered out (calendar)
            "https://adams.k12.mi.us/news.php",
            "https://adams.k12.mi.us/elementary-lunch.php",
            "https://adams.k12.mi.us/elementary-directory.php",
            "https://adams.k12.mi.us/district-foundation.php",
            "https://adams.k12.mi.us/district-alumni.php",
            "https://adams.k12.mi.us/high-school-schedule.php",
            "https://adams.k12.mi.us/district-state-reporting.php",
            "https://adams.k12.mi.us/",
            "https://adams.k12.mi.us/high-school-directory.php",
            "https://adams.k12.mi.us/elementary-pto.php",
            "https://adams.k12.mi.us/school-song.php",
            "https://adams.k12.mi.us/index.php",
            "https://adams.k12.mi.us/district-drills.php",
            "https://adams.k12.mi.us/news-view.php?target=980",
            "https://adams.k12.mi.us/high-school-lunch.php",
            "https://adams.k12.mi.us/covid.php",
            "https://adams.k12.mi.us/contact.php",
            "https://adams.k12.mi.us/district-usf-rfp.php",
            "https://adams.k12.mi.us/news-view.php?target=981",
            "https://adams.k12.mi.us/news-view.php?target=979",
            "https://adams.k12.mi.us/music.php",
            "https://adams.k12.mi.us/district-board.php"
        ],
        "should_include": [
            "https://adams.k12.mi.us/district-board.php",  # Board page
            "https://adams.k12.mi.us/contact.php",  # Contact page
        ],
        "should_exclude": [
            "https://adams.k12.mi.us/calendar.php",  # Calendar
            "https://adams.k12.mi.us/high-school-lunch.php",  # Lunch menu
            "https://adams.k12.mi.us/school-song.php",  # School song
        ]
    },
]


class TestSuperintendentExtraction:
    """Test superintendent extraction with real data"""

    @pytest.mark.parametrize("test_case", EXTRACTION_TEST_CASES, ids=lambda x: x["id"])
    def test_extraction(self, test_case):
        """Test extraction returns expected results"""
        result = extract_superintendent(
            text=test_case["input_text"],
            district_name=test_case["district_name"]
        )

        # Check expected fields
        expected = test_case["expected"]
        assert result.is_empty == expected["is_empty"], \
            f"Expected is_empty={expected['is_empty']}, got {result.is_empty}"

        if not expected["is_empty"]:
            # For successful extractions, verify all fields
            assert result.name == expected["name"], \
                f"Expected name='{expected['name']}', got '{result.name}'"
            assert result.email == expected["email"], \
                f"Expected email='{expected['email']}', got '{result.email}'"
            assert result.phone == expected["phone"], \
                f"Expected phone='{expected['phone']}', got '{result.phone}'"

            # Title should contain "Superintendent"
            if expected["title"]:
                assert "Superintendent" in result.title, \
                    f"Title should contain 'Superintendent', got '{result.title}'"

        # Check reasoning quality
        if "reasoning_should_mention" in test_case:
            reasoning_lower = result.reasoning.lower()
            for keyword in test_case["reasoning_should_mention"]:
                assert keyword.lower() in reasoning_lower, \
                    f"Reasoning should mention '{keyword}', got: {result.reasoning}"

    @pytest.mark.parametrize("test_case", EXTRACTION_TEST_CASES, ids=lambda x: x["id"])
    def test_no_hallucination(self, test_case):
        """Ensure LLM doesn't hallucinate data that isn't in the input"""
        result = extract_superintendent(
            text=test_case["input_text"],
            district_name=test_case["district_name"]
        )

        # If extraction is empty, all fields should be None
        if result.is_empty:
            assert result.name is None, "Empty extraction should have name=None"
            assert result.email is None, "Empty extraction should have email=None"
            assert result.phone is None, "Empty extraction should have phone=None"
            assert result.title is None, "Empty extraction should have title=None"

        # If extraction found data, verify it's actually in the input
        if not result.is_empty:
            input_lower = test_case["input_text"].lower()

            if result.name:
                # Name should appear in input (allowing for formatting differences)
                name_parts = result.name.lower().split()
                assert any(part in input_lower for part in name_parts if len(part) > 2), \
                    f"Name '{result.name}' not found in input text"

            if result.email:
                # Email should be in input or constructed from explicit elements
                assert '@' in result.email, "Email must contain @"
                # Basic validation - don't allow obviously made-up emails
                assert result.email.lower() in input_lower or \
                       result.email.split('@')[0].lower() in input_lower, \
                    f"Email '{result.email}' not found in input"

            if result.phone:
                # Phone numbers should have digits from input
                phone_digits = ''.join(c for c in result.phone if c.isdigit())
                input_digits = ''.join(c for c in test_case["input_text"] if c.isdigit())
                assert phone_digits in input_digits, \
                    f"Phone '{result.phone}' digits not found in input"


class TestURLFiltering:
    """Test URL filtering with real data"""

    @pytest.mark.parametrize("test_case", URL_FILTERING_TEST_CASES, ids=lambda x: x["id"])
    def test_url_selection(self, test_case):
        """Test that URL filtering selects appropriate pages"""
        from services.extraction import filter_urls

        # Run URL filtering
        filtered = filter_urls(
            urls=test_case["all_urls"],
            district_name=test_case["district_name"],
            max_urls=10
        )

        # Check that important URLs are included
        for url in test_case["should_include"]:
            assert url in filtered, \
                f"Should include {url} in filtered results"

        # Check that irrelevant URLs are excluded
        for url in test_case["should_exclude"]:
            assert url not in filtered, \
                f"Should exclude {url} from filtered results"


# Helper to add new test cases from debug logs
def generate_test_case_from_debug_log(extraction_json_path, parsed_txt_path):
    """
    Helper to convert debug log files into test cases.

    Usage:
        python -c "from tests.test_superintendent_extraction import generate_test_case_from_debug_log;
                   generate_test_case_from_debug_log('debug_logs/.../extraction.json', 'debug_logs/.../parsed.txt')"
    """
    import json

    with open(extraction_json_path) as f:
        extraction_data = json.load(f)

    with open(parsed_txt_path) as f:
        parsed_text = f.read()

    test_case = {
        "id": f"generated_{extraction_data['url'].split('/')[-1]}",
        "description": f"Auto-generated from {extraction_json_path}",
        "district_name": "FILL_IN_DISTRICT_NAME",
        "input_text": parsed_text[:500] + "...",  # Truncate for readability
        "expected": {
            "is_empty": extraction_data["extraction"]["is_empty"],
            "name": extraction_data["extraction"].get("name"),
            "title": extraction_data["extraction"].get("title"),
            "email": extraction_data["extraction"].get("email"),
            "phone": extraction_data["extraction"].get("phone"),
        }
    }

    print("# Add this to EXTRACTION_TEST_CASES:")
    print(json.dumps(test_case, indent=2))


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
