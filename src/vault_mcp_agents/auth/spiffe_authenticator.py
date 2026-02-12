"""SPIFFE workload authentication against Vault Enterprise.

When deployed in containers, each MCP server and agent authenticates to Vault
using its X.509 SVID (SPIFFE Verifiable Identity Document).  Vault Enterprise
1.21+ provides a native SPIFFE auth method that:

  1. Validates the X.509 certificate chain against a configured trust domain.
  2. Extracts the SPIFFE ID from the certificate's URI SAN.
  3. Maps the SPIFFE ID to a Vault role, issuing a token with attached policies.

This module wraps that flow using the ``py-spiffe`` library for SVID
retrieval and ``hvac`` for Vault authentication.
"""

from __future__ import annotations

import datetime
import logging
import os
from typing import Any

import hvac

from vault_mcp_agents.audit.logger import AuditEvent, AuditLogger
from vault_mcp_agents.auth.workload_session import WorkloadSession

logger = logging.getLogger(__name__)


class SpiffeAuthenticationError(Exception):
    """Raised when SPIFFE authentication against Vault fails."""


class SpiffeAuthenticator:
    """Authenticates a workload using its SPIFFE SVID against Vault Enterprise.

    Usage::

        auth = SpiffeAuthenticator(
            vault_addr="http://vault:8200",
            trust_domain="vault-mcp-demo",
        )
        session = auth.authenticate_workload()
    """

    def __init__(
        self,
        vault_addr: str,
        trust_domain: str,
        spiffe_auth_mount: str = "spiffe",
    ) -> None:
        self._vault_addr = vault_addr
        self._trust_domain = trust_domain
        self._auth_mount = spiffe_auth_mount
        self._audit = AuditLogger(log_to_stdout=True)

    def authenticate_workload(self) -> WorkloadSession:
        """Fetch the workload's X.509 SVID and authenticate to Vault.

        Returns:
            A ``WorkloadSession`` with the Vault token and SPIFFE identity.

        Raises:
            SpiffeAuthenticationError: If SVID retrieval or Vault auth fails.
        """
        try:
            from spiffe import WorkloadApiClient
        except ImportError as exc:
            raise SpiffeAuthenticationError(
                "py-spiffe library is required for SPIFFE authentication. "
                "Install it with: pip install spiffe"
            ) from exc

        # Step 1 — Obtain X.509 SVID from the SPIFFE Workload API.
        endpoint = os.environ.get(
            "SPIFFE_ENDPOINT_SOCKET",
            "unix:///run/spire/sockets/agent.sock",
        )
        try:
            workload_client = WorkloadApiClient(endpoint)
            svid = workload_client.fetch_x509_svid()
            spiffe_id = str(svid.spiffe_id)
            cert_pem = svid.cert_chain_pem
            key_pem = svid.private_key_pem
        except Exception as exc:
            self._audit.log_event(
                AuditEvent.SPIFFE_AUTH_FAILURE,
                detail=f"Failed to fetch SVID: {exc}",
            )
            raise SpiffeAuthenticationError(
                f"Failed to fetch X.509 SVID from Workload API: {exc}"
            ) from exc

        logger.info("Obtained SVID: %s", spiffe_id)

        # Step 2 — Authenticate to Vault's SPIFFE auth method.
        try:
            client = hvac.Client(url=self._vault_addr)
            auth_response = client.auth.cert.login(
                name=self._auth_mount,
                cert_pem=cert_pem,
                key_pem=key_pem,
                mount_point=self._auth_mount,
            )
        except hvac.exceptions.VaultError as exc:
            self._audit.log_event(
                AuditEvent.SPIFFE_AUTH_FAILURE,
                spiffe_id=spiffe_id,
                detail=f"Vault SPIFFE login failed: {exc}",
            )
            raise SpiffeAuthenticationError(
                f"Vault SPIFFE authentication failed: {exc}"
            ) from exc

        vault_token: str = auth_response["auth"]["client_token"]
        policies: list[str] = auth_response["auth"]["policies"]
        ttl: int = auth_response["auth"]["lease_duration"]

        session = WorkloadSession(
            spiffe_id=spiffe_id,
            vault_token=vault_token,
            token_policies=frozenset(policies),
            created_at=datetime.datetime.now(datetime.UTC),
            ttl_seconds=ttl,
        )

        self._audit.log_event(
            AuditEvent.SPIFFE_AUTH_SUCCESS,
            spiffe_id=spiffe_id,
            detail=f"policies={policies}, ttl={ttl}s",
        )
        logger.info("SPIFFE auth successful: %s", session)
        return session

    def is_enabled(self) -> bool:
        """Check if SPIFFE authentication is configured."""
        return os.environ.get("SPIFFE_ENDPOINT_SOCKET") is not None
