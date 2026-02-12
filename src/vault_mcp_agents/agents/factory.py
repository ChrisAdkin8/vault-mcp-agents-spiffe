"""Agent factory: constructs LangChain agents wired to identity-gated MCP servers.

Pattern: Factory
-----------------
The factory encapsulates the multi-step process of building a usable agent:

  1. Resolve the policy for (human_role, agent_id).
  2. Build an ``IdentityContext`` combining agent + human identity.
  3. Start the MCP server subprocess with that context.
  4. Adapt the exposed MCP tools into LangChain tools.
  5. Construct a LangChain agent with those tools.

Callers only need a ``Session`` and an agent ID; the factory handles the rest.
"""

from __future__ import annotations

import logging
import os
import pathlib
from typing import Any

import yaml
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from vault_mcp_agents.agents.mcp_langchain_adapter import create_mcp_langchain_tools
from vault_mcp_agents.agents.mcp_http_adapter import create_mcp_http_langchain_tools
from vault_mcp_agents.auth.session import Session
from vault_mcp_agents.mcp.identity_context import IdentityContext
from vault_mcp_agents.policy.engine import PolicyEngine

logger = logging.getLogger(__name__)

_CONFIG_PATH = pathlib.Path(__file__).resolve().parents[3] / "config" / "settings.yaml"


def _load_config() -> dict[str, Any]:
    with open(_CONFIG_PATH) as fh:
        return yaml.safe_load(fh)


def _build_llm(config: dict[str, Any]) -> Any:
    """Construct the LangChain LLM from config."""
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "anthropic")
    model = llm_config.get("model", "claude-sonnet-4-20250514")
    temperature = llm_config.get("temperature", 0.0)
    api_key = llm_config.get("api_key") or None

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Anthropic API key not found. Set the ANTHROPIC_API_KEY "
                "environment variable or add 'api_key' under 'llm' in "
                "config/settings.yaml."
            )
        return ChatAnthropic(model=model, temperature=temperature, api_key=api_key)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Set the OPENAI_API_KEY "
                "environment variable or add 'api_key' under 'llm' in "
                "config/settings.yaml."
            )
        return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)
    raise ValueError(f"Unsupported LLM provider: {provider}")


async def build_agent(
    agent_id: str,
    session: Session,
    policy_engine: PolicyEngine,
) -> tuple[AgentExecutor, Any]:
    """Build a LangChain agent for *agent_id* acting on behalf of *session*.

    Returns:
        A tuple of (AgentExecutor, cleanup_handles) — the caller must keep
        cleanup_handles alive and close them when done.
    """
    config = _load_config()
    agent_config = config["agents"].get(agent_id)
    if agent_config is None:
        raise ValueError(f"No agent configuration found for '{agent_id}'")

    # Step 1 — Resolve capabilities from policy.
    policy = policy_engine.resolve(human_role=session.human_role, agent_id=agent_id)
    logger.info("Resolved policy for %s / %s: %s", session.human_role, agent_id, policy)

    # Step 2 — Validate LLM configuration early (before starting MCP server).
    llm = _build_llm(config)

    # Step 3 — Build identity context for the MCP server.
    gcp_config = config.get("gcp", {})
    identity = IdentityContext(
        agent_id=agent_id,
        human_id=session.human_id,
        human_role=session.human_role,
        vault_token=session.vault_token,
        allowed_tools=policy.allowed_tools,
        gcp_impersonated_account=agent_config["gcp_impersonated_account"],
        max_gcp_token_ttl=policy.max_gcp_token_ttl,
        gcp_project=gcp_config.get("project_id", ""),
        session_created_at=session.created_at.isoformat(),
        session_ttl_seconds=session.ttl_seconds,
    )

    # Step 4 + 5 — Start MCP server and adapt tools.
    server_config = config["mcp_servers"][agent_config["mcp_server"]]
    transport = server_config.get("transport", "stdio")

    if transport == "http":
        server_url = server_config["url"]
        logger.info("Connecting to MCP server via HTTP: %s", server_url)
        tools, cleanup = await create_mcp_http_langchain_tools(
            server_url=server_url,
            identity_context=identity,
        )
    else:
        tools, cleanup = await create_mcp_langchain_tools(
            server_command=server_config["command"],
            server_args=server_config["args"],
            identity_context=identity,
            vault_addr=config["vault"]["address"],
            gcp_mount=config["vault"]["gcp_secrets_mount"],
        )

    try:
        if not tools:
            logger.warning("No tools available for agent=%s, role=%s", agent_id, session.human_role)

        # Step 6 — Construct the LangChain agent.
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                f"You are the {agent_id} agent.  You operate on behalf of user "
                f"'{session.human_id}' (role: {session.human_role}).  "
                f"You have access to these tools: {[t.name for t in tools]}.  "
                "Use them to fulfil the user's requests.  If a tool is not in "
                "your list, tell the user you lack permission for that action.",
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    except BaseException:
        await cleanup.aclose()
        raise

    return executor, cleanup
