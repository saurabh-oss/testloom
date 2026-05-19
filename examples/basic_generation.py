"""Basic test case generation example.

Prerequisites:
    pip install testloom
    export TESTLOOM_LLM__API_KEY=your-api-key

Usage:
    python examples/basic_generation.py
"""

import asyncio
from pathlib import Path

from testloom import Settings, GenerationRequest, RequirementGenerator
from testloom.formatters import get_formatter
from testloom.gateway.registry import GatewayRegistry


async def main():
    # Load configuration (from testloom.yaml or environment)
    settings = Settings.load()

    # Create the LLM gateway
    gateway = GatewayRegistry.create(settings.llm)

    # Create the generator
    generator = RequirementGenerator(gateway, settings)

    # Define what to generate
    request = GenerationRequest(
        requirement_text="""
        As a customer, I want to add items to my shopping cart so that I can
        purchase multiple products in a single transaction.

        Acceptance Criteria:
        - User can add any available product to the cart
        - Cart shows item count and total price
        - User can update quantity or remove items
        - Cart persists across browser sessions
        - Maximum 50 items per cart
        """,
        max_cases=15,
        include_test_data=True,
    )

    # Generate test cases
    print("Generating test cases...")
    suite = await generator.generate(request)

    # Print summary
    print(f"\nGenerated {suite.total_cases} test cases:")
    for test_type, cases in suite.by_type.items():
        print(f"  {test_type.value}: {len(cases)}")

    # Output as Markdown
    formatter = get_formatter("markdown")
    output = formatter.format(suite)
    output_path = Path("output/shopping_cart_tests.md")
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(output)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
