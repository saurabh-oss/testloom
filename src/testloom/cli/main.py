"""TestLoom CLI — command-line interface for test case generation."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from testloom.core.config import Settings
from testloom.core.models import GenerationRequest, TestType
from testloom.formatters import get_formatter
from testloom.gateway.registry import GatewayRegistry
from testloom.generators.requirement_generator import RequirementGenerator

console = Console()
err_console = Console(stderr=True)


def _parse_types(types_str: str) -> list[TestType]:
    """Parse comma-separated test type names into TestType enum values."""
    valid = {t.value for t in TestType}
    result = []
    for raw in types_str.split(","):
        name = raw.strip().lower().replace("-", "_").replace(" ", "_")
        if name not in valid:
            err_console.print(
                f"[red]Unknown test type '{raw}'. Valid: {', '.join(sorted(valid))}[/red]"
            )
            raise SystemExit(1)
        result.append(TestType(name))
    return result or [TestType.FUNCTIONAL, TestType.NEGATIVE, TestType.EDGE_CASE]


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose/debug output")
@click.pass_context
def cli(ctx: click.Context, config: str | None, verbose: bool) -> None:
    """TestLoom — AI-powered test case generation."""
    ctx.ensure_object(dict)
    settings = Settings.load(config)
    if verbose:
        settings.log_level = "DEBUG"
    ctx.obj["settings"] = settings
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), help="Requirement file (txt, md)")
@click.option("--text", "-t", help="Inline requirement text")
@click.option("--output", "-o", "output_path", type=click.Path(), help="Output file path")
@click.option(
    "--format", "-f", "fmt",
    default="markdown",
    type=click.Choice(["json", "markdown", "md", "csv", "junit", "xml"], case_sensitive=False),
    help="Output format",
    show_default=True,
)
@click.option("--max-cases", default=20, show_default=True, help="Maximum test cases to generate")
@click.option("--model", "-m", help="Override LLM model (e.g. ollama/llama3)")
@click.option(
    "--types",
    default=None,
    help="Comma-separated test types: functional,negative,edge_case,boundary,integration,api,regression,smoke",
)
@click.option("--context", default=None, help="Additional context to guide generation")
@click.pass_context
def generate(
    ctx: click.Context,
    input_path: str | None,
    text: str | None,
    output_path: str | None,
    fmt: str,
    max_cases: int,
    model: str | None,
    types: str | None,
    context: str | None,
) -> None:
    """Generate test cases from a requirement."""
    settings: Settings = ctx.obj["settings"]

    if model:
        settings.llm.model = model

    if input_path:
        requirement = Path(input_path).read_text(encoding="utf-8")
    elif text:
        requirement = text
    else:
        err_console.print("[red]Provide --input file or --text requirement[/red]")
        raise SystemExit(1)

    test_types = _parse_types(types) if types else [
        TestType.FUNCTIONAL, TestType.NEGATIVE, TestType.EDGE_CASE
    ]

    request = GenerationRequest(
        requirement_text=requirement,
        max_cases=max_cases,
        output_format=fmt if fmt not in ("md",) else "markdown",
        test_types=test_types,
        context=context,
    )

    console.print(Panel(
        f"[bold cyan]Generating test cases[/bold cyan]\n"
        f"[dim]Model:[/dim]    {settings.llm.provider}/{settings.llm.model}\n"
        f"[dim]Types:[/dim]    {', '.join(t.value for t in test_types)}\n"
        f"[dim]Max:[/dim]      {max_cases}   [dim]Format:[/dim] {fmt}",
        title="[bold]TestLoom[/bold]",
        border_style="cyan",
    ))

    gateway = GatewayRegistry.create(settings.llm)
    generator = RequirementGenerator(gateway, settings)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  console=console, transient=True) as progress:
        progress.add_task("Calling LLM…", total=None)
        suite = asyncio.run(generator.generate(request))

    formatter = get_formatter(fmt)
    output = formatter.format(suite)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(output, encoding="utf-8")
        console.print(f"[green]✓ {suite.total_cases} test cases written → {output_path}[/green]")
    else:
        console.print(output)

    _print_summary(suite)


@cli.command()
@click.argument("requirements_file", type=click.Path(exists=True))
@click.option("--output-dir", "-o", "output_dir", default="output", show_default=True, help="Directory for output files")
@click.option(
    "--format", "-f", "fmt",
    default="markdown",
    type=click.Choice(["json", "markdown", "csv", "junit"], case_sensitive=False),
    show_default=True,
)
@click.option("--max-cases", default=15, show_default=True, help="Max test cases per requirement")
@click.option("--model", "-m", help="Override LLM model")
@click.option("--concurrency", default=3, show_default=True, help="Parallel LLM calls (respect rate limits)")
@click.pass_context
def batch(
    ctx: click.Context,
    requirements_file: str,
    output_dir: str,
    fmt: str,
    max_cases: int,
    model: str | None,
    concurrency: int,
) -> None:
    """Batch-generate test cases from a file of requirements.

    REQUIREMENTS_FILE should be a text file with one requirement per line,
    or a markdown file with requirements separated by blank lines (paragraphs).
    Lines starting with '#' are treated as section headers and skipped.
    """
    settings: Settings = ctx.obj["settings"]
    if model:
        settings.llm.model = model

    raw = Path(requirements_file).read_text(encoding="utf-8")

    # Split: try blank-line paragraphs first, fall back to single lines
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    requirements = [p for p in paragraphs if not p.startswith("#")]

    if not requirements:
        err_console.print(f"[red]No requirements found in {requirements_file}[/red]")
        raise SystemExit(1)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    formatter = get_formatter(fmt)
    ext = formatter.extension

    console.print(Panel(
        f"[bold cyan]Batch generation[/bold cyan]\n"
        f"[dim]Requirements:[/dim] {len(requirements)}\n"
        f"[dim]Model:[/dim]        {settings.llm.provider}/{settings.llm.model}\n"
        f"[dim]Concurrency:[/dim]  {concurrency}   [dim]Output:[/dim] {out_dir}/",
        title="[bold]TestLoom Batch[/bold]",
        border_style="cyan",
    ))

    requests = [
        GenerationRequest(
            requirement_text=req,
            max_cases=max_cases,
            output_format=fmt,
        )
        for req in requirements
    ]

    gateway = GatewayRegistry.create(settings.llm)
    generator = RequirementGenerator(gateway, settings)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  console=console) as progress:
        task = progress.add_task(f"Generating for {len(requests)} requirements…", total=len(requests))

        async def _run() -> list:
            results = []
            sem = asyncio.Semaphore(concurrency)

            async def _one(req: GenerationRequest, idx: int):
                async with sem:
                    suite = await generator.generate(req)
                    progress.advance(task)
                    return idx, suite

            pairs = await asyncio.gather(*(_one(r, i) for i, r in enumerate(requests)))
            return [s for _, s in sorted(pairs)]

        suites = asyncio.run(_run())

    total_cases = sum(s.total_cases for s in suites)
    console.print(f"\n[green]✓ Generated {total_cases} test cases across {len(suites)} suites[/green]")

    for i, suite in enumerate(suites):
        out_file = out_dir / f"suite_{i + 1:03d}.{ext}"
        out_file.write_text(formatter.format(suite), encoding="utf-8")

    console.print(f"[green]✓ Files written to {out_dir}/[/green]")

    table = Table(title="Batch Summary", border_style="cyan")
    table.add_column("#", style="dim")
    table.add_column("Requirement", max_width=60)
    table.add_column("Cases", justify="right")
    table.add_column("File", style="dim")
    for i, (req, suite) in enumerate(zip(requirements, suites)):
        table.add_row(
            str(i + 1),
            req[:60] + ("…" if len(req) > 60 else ""),
            str(suite.total_cases),
            f"suite_{i + 1:03d}.{ext}",
        )
    console.print(table)


@cli.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show current configuration."""
    settings: Settings = ctx.obj["settings"]
    console.print(Panel(
        f"[bold]Provider:[/bold]       {settings.llm.provider}\n"
        f"[bold]Model:[/bold]          {settings.llm.model}\n"
        f"[bold]Temperature:[/bold]    {settings.llm.temperature}\n"
        f"[bold]Max tokens:[/bold]     {settings.llm.max_tokens}\n"
        f"[bold]Retry attempts:[/bold] {settings.llm.retry_attempts}\n"
        f"[bold]Retry backoff:[/bold]  {settings.llm.retry_backoff}s\n"
        f"[bold]Template dir:[/bold]   {settings.prompt_template_dir}\n"
        f"[bold]Output dir:[/bold]     {settings.output_dir}\n"
        f"[bold]Log level:[/bold]      {settings.log_level}",
        title="[bold]Configuration[/bold]",
        border_style="cyan",
    ))


@cli.command()
def providers() -> None:
    """List available LLM providers and example model strings."""
    table = Table(title="Available LLM Providers", border_style="cyan")
    table.add_column("Provider")
    table.add_column("Example model string")
    table.add_column("Notes")
    rows = [
        ("openai",     "gpt-4o",                           "Default — requires OPENAI_API_KEY"),
        ("anthropic",  "anthropic/claude-sonnet-4-6",      "Requires ANTHROPIC_API_KEY"),
        ("ollama",     "ollama/llama3",                    "Local — zero cost, run `ollama pull llama3`"),
        ("azure",      "azure/my-deployment",              "Requires AZURE_API_KEY + api_base"),
        ("bedrock",    "bedrock/anthropic.claude-3",       "AWS — requires AWS credentials"),
        ("litellm",    "any LiteLLM model string",         "100+ providers via model string convention"),
    ]
    for provider, model, note in rows:
        table.add_row(provider, model, note)
    console.print(table)


@cli.command()
def version() -> None:
    """Show version information."""
    from testloom import __version__
    console.print(f"[bold]testloom[/bold] {__version__}")


def _print_summary(suite) -> None:
    table = Table(title="Generation Summary", show_header=True, border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Total cases", str(suite.total_cases))
    for tt, cases in suite.by_type.items():
        table.add_row(f"  {tt.value}", str(len(cases)))
    meta = suite.generation_metadata
    if "latency_ms" in meta:
        table.add_row("Latency", f"{meta['latency_ms']:.0f} ms")
    if "tokens" in meta and meta["tokens"]:
        table.add_row("Tokens used", str(meta["tokens"].get("total_tokens", "—")))
    console.print(table)


if __name__ == "__main__":
    cli()
