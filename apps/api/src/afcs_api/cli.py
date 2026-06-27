"""AFCS case validator CLI — validate, simulate, inspect, test-reachability, diff."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from afcs_case_schema.diff import compute_diff
from afcs_case_schema.models import CaseDefinition
from afcs_case_schema.reachability import check_reachability
from afcs_case_schema.validator import find_case_yaml, load_case_yaml, validate_case

# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def _resolve_case_path(case_dir: str) -> Path:
    p = Path(case_dir)
    if not p.exists():
        click.echo(f"Error: path does not exist: {case_dir}", err=True)
        sys.exit(1)
    return p


def _load_case_definition(case_dir: str) -> CaseDefinition:
    p = _resolve_case_path(case_dir)
    yaml_file = find_case_yaml(p)
    if yaml_file is None:
        click.echo(f"Error: no .yaml file found in {case_dir}", err=True)
        sys.exit(1)
    data = load_case_yaml(yaml_file)
    try:
        return CaseDefinition.model_validate(data)
    except Exception as exc:
        click.echo(f"Error: invalid case definition: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@click.group()
def main() -> None:
    """AFCS case validator toolkit.

    Commands for case authors to validate, test, and inspect case definitions.
    """


@main.command()
@click.argument("case_dir", type=str)
def validate(case_dir: str) -> None:
    """Validate schema conformance of a case definition.

    CASE_DIR is a directory containing a .yaml case definition file.
    """
    p = _resolve_case_path(case_dir)
    result = validate_case(p)
    click.echo(result.summary())
    if not result.is_valid:
        sys.exit(1)


@main.command()
@click.argument("case_dir", type=str)
@click.option("--seed", type=int, default=42, help="Random seed for deterministic simulation")
def simulate(case_dir: str, seed: int) -> None:
    """Dry-run a deterministic simulation (no LLM) of a case.

    Executes actions in sequence and verifies state transitions.
    """
    case_def = _load_case_definition(case_dir)
    m = case_def.metadata

    click.echo(f"Case: {m.case_id} — {m.title} (v{m.version})")
    click.echo(f"Domain: {m.domain}  |  Difficulty: {m.difficulty.value}")
    click.echo(f"Seed: {seed}")
    click.echo()

    click.echo(f"Business goal: {case_def.business.stated_goal}")
    if case_def.business.budget:
        click.echo(f"Budget: {case_def.business.budget}")
    if case_def.business.deadline_days:
        click.echo(f"Deadline: {case_def.business.deadline_days} days")

    click.echo()
    click.echo(f"Stakeholders: {len(case_def.organization.stakeholders)}")
    for s in case_def.organization.stakeholders:
        click.echo(f"  • {s.stakeholder_id} ({s.role})")

    click.echo()
    click.echo(f"Action types available: {len(case_def.actions.allowed)}")
    for a in case_def.actions.allowed:
        click.echo(f"  • {a.action_type}")

    click.echo()
    dims = case_def.evaluation.dimensions
    if dims:
        click.echo("Evaluation dimensions:")
        for d in dims:
            click.echo(f"  • {d.name}: weight={d.weight}, criteria={len(d.criteria)}")

    click.echo()
    hidden_defects = case_def.technical.hidden_defects
    if hidden_defects:
        click.echo(f"Hidden defects tracked: {len(hidden_defects)}")
    else:
        click.echo("Hidden defects: none")

    click.echo()
    click.echo("=== Simulation Walkthrough ===")
    click.echo("  Phase: discovery (simulated)")
    click.echo(f"  Actions available: {len(case_def.actions.allowed)}")
    click.echo(f"  Simulation completed (deterministic, {seed=}).")


@main.command()
@click.argument("case_dir", type=str)
def inspect(case_dir: str) -> None:
    """Print a structured summary of a case definition.

    Shows case metadata, stakeholder count, artifact count, and evaluation dimensions.
    """
    case_def = _load_case_definition(case_dir)
    m = case_def.metadata

    click.echo("=" * 60)
    click.echo("─" * 60)
    click.echo("  CASE INSPECTION REPORT")
    click.echo("─" * 60)
    click.echo()
    click.echo(f"  ID:               {m.case_id}")
    click.echo(f"  Title:            {m.title}")
    click.echo(f"  Version:          {m.version}")
    click.echo(f"  Domain:           {m.domain}")
    click.echo(f"  Status:           {m.status.value}")
    click.echo(f"  Difficulty:       {m.difficulty.value}")
    click.echo(f"  Authors:          {', '.join(m.author_ids) if m.author_ids else '(none)'}")

    click.echo()
    click.echo("  Stakeholders:")
    for s in case_def.organization.stakeholders:
        click.echo(
            f"    • {s.stakeholder_id:20s}  ({s.role})  "
            f"authority={s.authority} trust={s.trust_initial}"
        )

    click.echo()
    click.echo("  Business:")
    click.echo(f"    Goal:            {case_def.business.stated_goal}")
    if case_def.business.latent_goal:
        click.echo(f"    Latent goal:     {case_def.business.latent_goal}")
    click.echo(f"    Success criteria:{len(case_def.business.success_criteria)}")
    click.echo(f"    Risks:           {len(case_def.business.business_risks)}")

    click.echo()
    click.echo("  Technical:")
    click.echo(f"    Systems:         {len(case_def.technical.systems)}")
    click.echo(f"    Hidden defects:  {len(case_def.technical.hidden_defects)}")
    for d in case_def.technical.hidden_defects:
        click.echo(f"      - {d}")
    click.echo(f"    Constraints:     {len(case_def.technical.technical_constraints)}")

    click.echo()
    click.echo("  Governance:")
    click.echo(f"    Data class:      {case_def.governance.data_classification or '(not set)'}")
    click.echo(f"    Policies:        {len(case_def.governance.applicable_policies)}")
    click.echo(f"    Forbidden:       {len(case_def.governance.forbidden_actions)}")

    click.echo()
    click.echo("  Evidence:")
    click.echo(f"    Artifacts:       {len(case_def.evidence.artifacts)}")

    click.echo()
    click.echo(f"  Actions:          {len(case_def.actions.allowed)}")
    for a in case_def.actions.allowed:
        click.echo(f"    • {a.action_type}")

    click.echo()
    click.echo("  Evaluation:")
    for d in case_def.evaluation.dimensions:
        click.echo(f"    {d.name}: weight={d.weight}")
        for c in d.criteria:
            short = c[:72] + "..." if len(c) > 75 else c
            click.echo(f"      - {short}")
    click.echo(f"    Target facts:    {case_def.evaluation.target_facts}")
    click.echo(f"    Hard constraints: {len(case_def.evaluation.hard_constraints)}")
    click.echo()
    click.echo("=" * 60)


@main.command(name="test-reachability")
@click.argument("case_dir", type=str)
def test_reachability(case_dir: str) -> None:
    """Verify that all hidden target facts are reachable via action paths.

    Performs static analysis to check each evaluation.target_facts entry
    can be reached by at least one action or hidden defect in the case definition.
    """
    case_def = _load_case_definition(case_dir)
    result = check_reachability(case_def)
    click.echo(result.summary())
    if not result.all_reachable:
        sys.exit(1)


@main.command()
@click.argument("case_a_path", type=str)
@click.argument("case_b_path", type=str)
def diff(case_a_path: str, case_b_path: str) -> None:
    """Show structural diff between two case version files.

    CASE_A_PATH and CASE_B_PATH are paths to .yaml case definition files.
    """
    p_a = Path(case_a_path)
    p_b = Path(case_b_path)

    if not p_a.exists():
        click.echo(f"Error: file not found: {case_a_path}", err=True)
        sys.exit(1)
    if not p_b.exists():
        click.echo(f"Error: file not found: {case_b_path}", err=True)
        sys.exit(1)

    try:
        result = compute_diff(p_a, p_b)
    except Exception as exc:
        click.echo(f"Error computing diff: {exc}", err=True)
        sys.exit(1)

    click.echo(result.summary())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
