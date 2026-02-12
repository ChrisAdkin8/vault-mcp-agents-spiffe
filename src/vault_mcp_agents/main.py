"""CLI entry point — ties together configuration, login, and agent interaction."""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vault-MCP Agents: identity-gated LangChain agents",
    )
    parser.add_argument(
        "--config",
        default=str(pathlib.Path(__file__).resolve().parents[2] / "config" / "settings.yaml"),
        help="Path to settings.yaml",
    )
    parser.add_argument(
        "--policies",
        default=None,
        help="Path to capabilities.yaml (default: policies/capabilities.yaml)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    with open(args.config) as fh:
        config = yaml.safe_load(fh)

    vault_cfg = config.get("vault", {})

    from vault_mcp_agents.prompt.cli import run_cli

    run_cli(
        vault_addr=vault_cfg.get("address", "http://127.0.0.1:8200"),
        auth_method=vault_cfg.get("auth_method", "userpass"),
        policy_path=args.policies,
    )


if __name__ == "__main__":
    main()
