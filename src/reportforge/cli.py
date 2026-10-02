from enum import Enum
from typing import List
import typer
from . import db

app = typer.Typer(help="ReportForge - Pentest findings manager")


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


@app.command()
def new(
    name: str = typer.Argument(..., help="Engagement name"),
    client: str = typer.Option(..., "--client", "-c"),
    scope: List[str] = typer.Option(..., "--scope", "-s", help="Authorized targets"),
):
    """Create a new engagement with its authorized scope."""
    conn = db.connect()
    cur = conn.execute(
        "INSERT INTO engagements (name, client) VALUES (?, ?)", (name, client)
    )
    eid = cur.lastrowid
    conn.executemany(
        "INSERT INTO scope (engagement_id, target) VALUES (?, ?)",
        [(eid, t) for t in scope],
    )
    conn.commit()
    typer.echo(f"Created engagement #{eid} with {len(scope)} target(s) in scope.")


@app.command()
def add(
    engagement_id: int = typer.Argument(...),
    title: str = typer.Option(..., "--title", "-t"),
    severity: Severity = typer.Option(..., "--severity"),
    target: str = typer.Option(..., "--target"),
    description: str = typer.Option("", "--desc"),
    remediation: str = typer.Option("", "--fix"),
):
    """Add a finding. Rejects targets outside the authorized scope."""
    conn = db.connect()
    in_scope = conn.execute(
        "SELECT 1 FROM scope WHERE engagement_id=? AND target=?",
        (engagement_id, target),
    ).fetchone()
    if not in_scope:
        typer.secho(f"Target {target} is OUT OF SCOPE!", fg=typer.colors.RED)
        raise typer.Exit(1)
    conn.execute(
        "INSERT INTO findings "
        "(engagement_id, title, severity, target, description, remediation) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (engagement_id, title, severity.value, target, description, remediation),
    )
    conn.commit()
    typer.echo("Finding added.")


@app.command("list")
def list_findings(engagement_id: int):
    """List findings sorted by severity."""
    conn = db.connect()
    order = (
        "CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 "
        "WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END"
    )
    rows = conn.execute(
        f"SELECT * FROM findings WHERE engagement_id=? ORDER BY {order}",
        (engagement_id,),
    ).fetchall()
    for r in rows:
        typer.echo(f"[{r['severity'].upper():8}] {r['title']}  ->  {r['target']}")


if __name__ == "__main__":
    app()