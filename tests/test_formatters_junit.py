"""Tests for the JUnit XML formatter."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from testloom.formatters import JUnitFormatter, get_formatter
from testloom.core.models import TestCase, TestStep, TestSuite, TestType, Priority


@pytest.fixture
def sample_suite() -> TestSuite:
    return TestSuite(
        id="suite-test",
        name="Sample Suite",
        test_cases=[
            TestCase(
                id="tc-001",
                title="Verify login",
                description="Happy path login",
                preconditions=["User exists"],
                steps=[
                    TestStep(step_number=1, action="Enter email", expected_result="Email accepted", test_data="user@example.com"),
                    TestStep(step_number=2, action="Click login", expected_result="Redirect to dashboard"),
                ],
                expected_outcome="User is logged in",
                test_type=TestType.FUNCTIONAL,
                priority=Priority.CRITICAL,
                tags=["login"],
                requirement_ids=["REQ-001"],
                confidence_score=0.95,
                model_used="gpt-4o",
            ),
            TestCase(
                id="tc-002",
                title="Verify login fails with wrong password",
                description="Negative test",
                expected_outcome="Error shown",
                test_type=TestType.NEGATIVE,
                priority=Priority.HIGH,
            ),
        ],
        generation_metadata={"model": "gpt-4o", "provider": "openai"},
    )


def test_junit_produces_valid_xml(sample_suite):
    fmt = JUnitFormatter()
    output = fmt.format(sample_suite)
    # Must not raise
    root = ET.fromstring(output)
    assert root.tag == "testsuites"


def test_junit_testsuite_attributes(sample_suite):
    output = JUnitFormatter().format(sample_suite)
    root = ET.fromstring(output)
    ts = root.find("testsuite")
    assert ts is not None
    assert ts.attrib["tests"] == "2"
    assert ts.attrib["failures"] == "0"
    assert ts.attrib["name"] == "Sample Suite"


def test_junit_testcase_names(sample_suite):
    output = JUnitFormatter().format(sample_suite)
    root = ET.fromstring(output)
    ts = root.find("testsuite")
    testcases = ts.findall("testcase")
    assert len(testcases) == 2
    assert "tc-001" in testcases[0].attrib["name"]
    assert "tc-002" in testcases[1].attrib["name"]


def test_junit_testcase_classname(sample_suite):
    output = JUnitFormatter().format(sample_suite)
    root = ET.fromstring(output)
    ts = root.find("testsuite")
    tcs = ts.findall("testcase")
    assert tcs[0].attrib["classname"] == "functional"
    assert tcs[1].attrib["classname"] == "negative"


def test_junit_system_out_contains_steps(sample_suite):
    output = JUnitFormatter().format(sample_suite)
    root = ET.fromstring(output)
    tc = root.find("testsuite/testcase")
    sysout = tc.find("system-out")
    assert sysout is not None
    assert "Enter email" in sysout.text
    assert "user@example.com" in sysout.text


def test_get_formatter_junit():
    fmt = get_formatter("junit")
    assert isinstance(fmt, JUnitFormatter)
    assert get_formatter("xml").extension == "xml"


def test_junit_extension():
    assert JUnitFormatter().extension == "xml"
