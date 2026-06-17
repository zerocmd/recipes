from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Command Zero
    cz_api_base_url: str = "https://api.cmdzero.io/public/v1"
    cz_org_id: str
    cz_bearer_token: str

    # Splunk REST + HEC
    splunk_rest_url: str  # search head that owns index=notable, e.g. https://localhost:8089
    # REST endpoint of the ES search head, used for the notable_update writeback.
    # On a single-instance deployment ES runs on the same search head, so leave this
    # blank and it falls back to splunk_rest_url. On Splunk Cloud (and distributed
    # on-prem) ES often lives on a separate search head — point this at it.
    # Only consulted when splunk_es_writeback is True.
    splunk_es_rest_url: str = ""
    splunk_svc_token: str
    splunk_es_writeback: bool = True  # set False to skip notable_update comment (e.g. no ES licence)
    splunk_hec_url: str = ""  # optional; empty = HEC writeback disabled
    splunk_hec_token: str = ""
    # Verify Splunk's TLS certificate (REST + HEC). Defaults to True; set to False
    # only when Splunk presents a self-signed certificate.
    splunk_verify_tls: bool = True

    # Index names
    notable_index: str = "notable"
    enrichment_index: str = "cz_enrichment"

    # Poll intervals
    splunk_poll_interval: int = 300   # seconds between Splunk polls
    poll_window_overlap: int = 600    # seconds of overlap to avoid checkpoint gaps
    cz_poll_interval: int = 300       # base seconds between CZ completion polls
    cz_poll_max_backoff: int = 1800   # per-record backoff ceiling (seconds)
    cz_submit_delay: float = 2.0     # seconds to pause between consecutive CZ submissions

    # Behaviour
    alert_type_prefix: str = "SplunkES"

    # NOT YET IMPLEMENTED — reserved flag. Reading it has no effect anywhere in the
    # codebase today; it exists so the config surface and docs are stable for when
    # the feature lands.
    #
    # Intended behaviour once implemented:
    #   When True, the writeback step (connector._writeback_ready) should set the ES
    #   notable's disposition from the CZ verdict, in addition to posting the comment.
    #   Sketch of the work:
    #     1. Map the CZ verdict string -> a Splunk ES disposition id. ES ships defaults
    #        disposition:1 (True Positive - Suspicious Activity) .. disposition:5
    #        (False Positive - Incorrect Analytic Logic), plus any custom ones the
    #        customer has defined. The mapping is environment-specific, so it likely
    #        belongs in a small dict/config (e.g. VERDICT_TO_DISPOSITION) rather than
    #        hard-coded here. Decide the fallback when a verdict has no mapping
    #        (recommended: leave disposition unset rather than guessing).
    #     2. Pass the resolved disposition id to splunk.write_verdict, which would add
    #        a `disposition` field to the /services/notable_update form POST alongside
    #        `ruleUIDs` and `comment` (the notable_update endpoint accepts it).
    #     3. Gate the whole step on this flag so the default (False) preserves today's
    #        comment-only behaviour.
    #
    # This cannot be built or verified without access to a live Splunk Enterprise
    # Security instance: notable_update / dispositions are an ES feature and are absent
    # on Splunk Enterprise Trial (the same constraint that makes the comment writeback
    # untestable locally — see README "Known limitations"). Implement and test it
    # against a real ES deployment, then wire it into _writeback_ready and write_verdict.
    auto_disposition: bool = False   # set notable disposition from CZ verdict (off by default)

    # State DB
    db_path: str = "connector.db"

    @field_validator("splunk_hec_url", "splunk_hec_token", mode="before")
    @classmethod
    def empty_string_as_default(cls, v):
        return v or ""

    @model_validator(mode="after")
    def default_es_rest_url(self):
        # ES writeback shares the core search head unless an ES-specific URL is set.
        if not self.splunk_es_rest_url:
            self.splunk_es_rest_url = self.splunk_rest_url
        return self
