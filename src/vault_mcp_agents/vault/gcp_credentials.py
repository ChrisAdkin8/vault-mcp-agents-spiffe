"""GCP credential retrieval from Vault's GCP secrets engine.

Pattern: Credential Brokering
------------------------------
No component in this system holds long-lived GCP credentials.  Instead, each
request for GCP access goes through Vault's GCP secrets engine, which returns
a short-lived OAuth2 access token scoped to a specific *impersonated account*.

The impersonated account is selected by combining the *agent identity* (which
account the agent is configured to use) with the *human session*.  The token
TTL is configured server-side on the Vault impersonated account (currently
5 minutes), enforced via GCP's ``generateAccessToken`` API ``lifetime``
field.

  - An operator using the data agent gets a 5 min token for BigQuery + GCS.
  - An analyst using the data agent gets a 5 min read-only token.
  - The same analyst using the compute agent gets a 5 min token limited to
    listing instances.
"""

from __future__ import annotations

import dataclasses
import logging

import hvac

from vault_mcp_agents.auth.session import Session

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class GCPAccessToken:
    """A short-lived GCP OAuth2 access token returned by Vault."""

    token: str
    ttl_seconds: int
    impersonated_account: str


class GCPCredentialError(Exception):
    """Raised when Vault cannot issue a GCP credential."""


class GCPCredentialBroker:
    """Fetches short-lived GCP tokens from Vault's GCP secrets engine."""

    def __init__(self, vault_addr: str, gcp_mount: str = "gcp") -> None:
        self._vault_addr = vault_addr
        self._gcp_mount = gcp_mount

    def get_access_token(
        self,
        session: Session,
        impersonated_account: str,
        requested_ttl: str = "5m",
    ) -> GCPAccessToken:
        """Request a GCP OAuth2 access token for *impersonated_account*.

        The token TTL is configured server-side on the Vault impersonated
        account (via GCP's ``generateAccessToken`` ``lifetime`` field).
        *requested_ttl* is accepted for logging/audit purposes only.

        Uses the *session's* Vault token so that Vault can enforce the human's
        policies on the GCP secrets engine path.
        """
        client = hvac.Client(url=self._vault_addr, token=session.vault_token)

        if session.is_expired:
            raise GCPCredentialError("Session has expired — re-authenticate")

        try:
            response = client.secrets.gcp.generate_impersonated_account_oauth2_access_token(
                name=impersonated_account,
                mount_point=self._gcp_mount,
            )
        except hvac.exceptions.VaultError as exc:
            raise GCPCredentialError(
                f"Vault GCP token generation failed for "
                f"impersonated_account={impersonated_account}: {exc}"
            ) from exc

        token_data = response["data"]
        logger.info(
            "Issued GCP token for impersonated_account=%s, session_user=%s, ttl=%ss",
            impersonated_account,
            session.human_id,
            token_data.get("token_ttl", "unknown"),
        )

        return GCPAccessToken(
            token=token_data["token"],
            ttl_seconds=token_data.get("token_ttl", 300),
            impersonated_account=impersonated_account,
        )
