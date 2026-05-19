"""TestLoom CLI — command-line interface for test case generation."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from testloom.core.config import Settings
from testloom.core.models import GenerationRequest, TestType
from testloom.formatters import get_formatter
from testloom.gateway.registry import GatewayRegistry
from testloom.generators.requirement_generator import RequirementGenerator

console = Console()


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, config: str | None, verbose: bool) -> None:
    """TestLoom — AI-powered test case generation."""
    ctx.ensure_object(dict)
    ctx.obj["settings"] = Settings.load(config)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), help="Input file")
@click.option("--text", "-t", help="Requirement text (alternative to --input)")
@click.option("--output", "-o", "output_path", type=click.Path(), help="Output file path")
@click.option("--format", "-f", "fmt", default="markdown", help="Output format: json, markdown, csv")
@click.option("--max-cases", default=20, help="Maximum test cases to generate")
@click.option("--model", "-m", help="Override LLM model")
@click.pass_context
def generate(
    ctx: click.Context,
    input_path: str | None,
    text: str | None,
    output_path: str | None,
    fmt: str,
    max_cases: int,
    model: str | None,
) -> None:
    """Generate test cases from requirements."""
    settings: Settings = ctx.obj["settings"]

    if model:
        settings.llm.model = model

    # Get requirement text
    if input_path:
        requirement = Path(input_path).read_text(encoding="utf-8")
    elif text:
        requirement = text
    else:
        console.print("[red]Provide --input file or --text requirement[/red]")
        raise SystemExit(1)

    request = GenerationRequest(
        requirement_text=requirement,
        max_cases=max_cases,
        output_format=fmt if fmt != "md" else "markdown",
    )

    console.print(Panel(
        f"[bold cyan]Generating test cases[/bold cyan]\n"
        f"Model: {settings.llm.provider}/{settings.llm.model}\n"
        f"Max cases: {max_cases} | Format: {fmt}",
        title="TestLoom",
        border_style="cyan",
    ))

    gateway = GatewayRegistry.create(settings.llm)
    generator = RequirementGenerator(gateway, settings)
    suite = asyncio.run(generator.generate(request))

    formatter = get_formatter(fmt)
    output = formatter.format(suite)

    if output_path:
        Path(output_path).write_text(output, encoding="utf-8")
        console.print(f"[green]✓ {suite.total_cases} test cases → {output_path}[/green]")
    else:
        console.print(output)

    # Summary table
    table = Table(title="Generation Summary", show_header=True, border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Total cases", str(suite.total_cases))
    for tt, cases in suite.by_type.items():
        table.add_row(f"  {tt.value}", str(len(cases)))
    meta = suite.generation_metadata
    if "latency_ms" in meta:
        table.add_row("Latency", f"{meta['latency_ms']:.0f} ms")
    if "tokens" in meta:
        table.add_row("Tokens used", str(meta["tokens"].get("total_tokens", "—")))
    console.print(table)


@cli.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show current configuration."""
    settings: Settings = ctx.obj["settings"]
    console.print(Panel(
        f"[bold]Provider:[/bold] {settings.llm.provider}\n"
        f"[bold]Model:[/bold] {settings.llm.model}\n"
        f"[bold]Temperature:[/bold] {settings.llm.temperature}\n"
        f"[bold]Max tokens:[/bold] {settings.llm.max_tokens}\n"
        f"[bold]Template dir:[/bold] {settings.prompt_template_dir}\n"
        f"[bold]Log level:[/bold] {settings.log_level}",
        title="Configuration",
        border_style="cyan",
    ))


@cli.command()
def providers() -> None:
    """List available LLM providers."""
    table = Table(title="Available Providers", border_style="cyan")
    table.add_column("Provider")
    table.add_column("Description")
    providers_info = [
        ("openai", "OpenAI GPT models (GPT-4o, GPT-4, etc.)"),
        ("anthropic", "Anthropic Claude models (via LiteLLM)"),
        ("ollama", "Local models via Ollama (Llama 3, Mistral, etc.)"),
        ("azure", "Azure OpenAI Service"),
        ("litellm", "Direct LiteLLM model strings (100+ providers)"),
    ]
    for name, desc in providers_info:
        table.add_row(name, desc)
    console.print(table)


@cli.command()
def version() -> None:
    """Show version."""
    from testloom import __version__
    console.print(f"testloom {__version__}")


if __name__ == "__main__":
    cli()
