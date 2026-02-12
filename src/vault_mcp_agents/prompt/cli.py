"""Interactive CLI prompt for login and agent interaction.

Pattern: Prompt Renderer
-------------------------
The CLI is the human-facing boundary.  It handles three responsibilities:

  1. **Login** — collect credentials and delegate to ``VaultAuthenticator``.
  2. **Agent selection** — let the user choose which agent to talk to.
  3. **Conversation loop** — forward natural-language input to the selected
     LangChain agent and display the response.

Rich and prompt_toolkit are used for display and input respectively.  The CLI
knows nothing about MCP, Vault internals, or GCP — it delegates everything to
the agent layer.
"""

from __future__ import annotations

import asyncio
import getpass
import logging
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vault_mcp_agents.agents.factory import build_agent
from vault_mcp_agents.auth.session import Session
from vault_mcp_agents.auth.vault_authenticator import (
    VaultAuthenticationError,
    VaultAuthenticator,
)
from vault_mcp_agents.policy.engine import PolicyEngine

logger = logging.getLogger(__name__)
console = Console()

AGENT_CHOICES = {
    "1": "data_agent",
    "2": "compute_agent",
}


def _print_banner() -> None:
    console.print(
        Panel(
            "[bold]Vault-MCP Agents[/bold]\n"
            "Identity-gated LangChain agents backed by MCP + Vault + GCP",
            border_style="blue",
        )
    )


def _login(vault_addr: str, auth_method: str) -> Session:
    """Prompt for credentials and authenticate against Vault."""
    console.print("\n[bold yellow]Login[/bold yellow] (authenticated via Vault)\n")

    username = input("  Username: ").strip()
    password = getpass.getpass("  Password: ")

    if not username or not password:
        console.print("[red]Username and password are required.[/red]")
        sys.exit(1)

    authenticator = VaultAuthenticator(vault_addr=vault_addr, auth_method=auth_method)

    try:
        session = authenticator.authenticate(username, password)
    except VaultAuthenticationError as exc:
        console.print(f"[red]Authentication failed:[/red] {exc}")
        sys.exit(1)

    console.print(f"\n  [green]Authenticated[/green] as [bold]{session.human_id}[/bold]")
    console.print(f"  Role: [bold]{session.human_role}[/bold]")
    console.print(f"  Token TTL: {session.ttl_seconds}s\n")
    return session


def _select_agent(session: Session, policy_engine: PolicyEngine) -> str:
    """Display available agents and let the user pick one."""
    table = Table(title="Available Agents")
    table.add_column("#", style="cyan")
    table.add_column("Agent", style="bold")
    table.add_column("Permitted Tools", style="green")

    for key, agent_id in AGENT_CHOICES.items():
        try:
            policy = policy_engine.resolve(session.human_role, agent_id)
            tools_str = ", ".join(sorted(policy.allowed_tools)) or "(none)"
        except Exception:
            tools_str = "(no policy defined)"
        table.add_row(key, agent_id, tools_str)

    console.print(table)
    choice = input("\nSelect agent [1/2]: ").strip()
    agent_id = AGENT_CHOICES.get(choice)

    if agent_id is None:
        console.print("[red]Invalid choice.[/red]")
        sys.exit(1)

    console.print(f"\n  Using agent: [bold]{agent_id}[/bold]\n")
    return agent_id


async def _conversation_loop(agent_id: str, session: Session, policy_engine: PolicyEngine) -> None:
    """Build the agent and run an interactive conversation."""
    console.print("[dim]Starting MCP server and building agent...[/dim]")

    executor, cleanup = await build_agent(
        agent_id=agent_id,
        session=session,
        policy_engine=policy_engine,
    )

    console.print("[green]Agent ready.[/green]  Type [bold]quit[/bold] to exit.\n")

    chat_history: list[tuple[str, str]] = []

    try:
        while True:
            try:
                user_input = input(f"[{session.human_id}] > ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                break

            if session.is_expired:
                console.print("[red]Session expired — please re-authenticate.[/red]")
                break

            result = await executor.ainvoke({
                "input": user_input,
                "chat_history": chat_history,
            })

            output = result.get("output", "(no response)")
            console.print(f"\n[bold blue]Agent:[/bold blue] {output}\n")
            chat_history.append(("human", user_input))
            chat_history.append(("ai", output))

    finally:
        # Clean up MCP client connections.
        if cleanup:
            await cleanup.aclose()


def run_cli(vault_addr: str, auth_method: str, policy_path: str | None = None) -> None:
    """Main entry point for the interactive CLI."""
    _print_banner()
    policy_engine = PolicyEngine(policy_path=policy_path)
    session = _login(vault_addr, auth_method)
    agent_id = _select_agent(session, policy_engine)
    asyncio.run(_conversation_loop(agent_id, session, policy_engine))
    console.print("\n[dim]Session ended.[/dim]")
