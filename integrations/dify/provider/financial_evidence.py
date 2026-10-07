from dify_plugin import ToolProvider


class FinancialEvidenceProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict) -> None:
        """Public, read-only endpoint; no credentials are requested or stored."""
        return None
