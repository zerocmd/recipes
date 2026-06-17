"""
Alert type allow-list and optional schemas for Splunk ES correlation searches.

SCHEMAS is the single source of truth for which alert types are forwarded to
Command Zero. Any alert type not present in SCHEMAS is silently dropped at
discovery time and never submitted.

The value for each entry controls how C0 extracts observables:

  - A list of TypeAnnotation dicts: the connector sends this schema on the
    first submission of the alert type so C0 knows which fields contain
    observables. C0 caches the schema per alertType, so subsequent
    submissions omit it.

  - None: the alert type is allowed but no schema is provided. C0 will use
    auto-schema to infer observables from the alert data automatically.

Adding a new alert type with an explicit schema:
  1. Add an entry to SCHEMAS keyed by the full alertType string.
  2. Use only types from VALID_C0_TYPES (sourced from
     autonomic/etc/ontology/type_name_mapping.yaml). Invalid types cause a
     400 "Unknown type" rejection at submission time; a warning is emitted
     at import time if any type in SCHEMAS is not in VALID_C0_TYPES.

Adding a new alert type with auto-schema (no explicit schema):
  1. Add an entry to SCHEMAS with None as the value.
  2. C0 will infer observables automatically on the first submission.
"""

import warnings

# ---------------------------------------------------------------------------
# Authoritative C0 lead types
# Sourced from: autonomic/etc/ontology/type_name_mapping.yaml
# ---------------------------------------------------------------------------

VALID_C0_TYPES: frozenset[str] = frozenset({
    # Alert metadata
    "ALERT_DESCRIPTION",
    "ALERT_ID",
    "ALERT_TIME",
    "ALERT_TITLE",
    # Common entity types
    "ASN",
    "COMPUTER_DNS_NAME",
    "CORTEX_AGENT_ID",
    "CVE_ID",
    "DOMAIN_NAME",
    "EMAIL_ADDRESS",
    "FILE_NAME",
    "FILE_PATH",
    "GUID",
    "HARDWARE_NETWORK_ADDRESS",
    "HASH",
    "HOST_NAME",
    "IDENTIFIER",
    "IP_ADDRESS",
    "IP_CONTACT_TYPE",
    "IP_PROTOCOL",
    "LOCAL_USERNAME",
    "MD5",
    "NETWORK_ADDRESS",
    "OPERATING_SYSTEM",
    "PATH",
    "PROCESS_ID",
    "PROVISIONING_STATUS",
    "REGISTRY_HIVE",
    "REGISTRY_KEY",
    "REGISTRY_KEY_VALUE",
    "SHA_1",
    "SHA_256",
    "SSH_PUBLIC_KEY",
    "STRING",
    "TIME",
    "URL",
    "USER",
    "USER_AGENT",
    "UUID",
    "WINDOWS_USER_SID",
    # AWS
    "AWS_ACCESS_KEY_ID",
    "AWS_ACCOUNT_ID",
    "AWS_ASSUMED_ROLE_ID",
    "AWS_ATHENA_USER_IDENTITY",
    "AWS_EC2_INSTANCE_ARN",
    "AWS_EC2_INSTANCE_ID",
    "AWS_EKS_CLUSTER_ARN",
    "AWS_GROUP_ARN",
    "AWS_GROUP_NAME",
    "AWS_GUARDDUTY_FINDING_ID",
    "AWS_INSTANCE_PROFILE_ARN",
    "AWS_INSTANCE_PROFILE_NAME",
    "AWS_ORGANIZATION_ID",
    "AWS_POLICY_ARN",
    "AWS_PRINCIPAL_ID",
    "AWS_RDS_USER_NAME",
    "AWS_REGION",
    "AWS_RESOURCE_NUMBER",
    "AWS_ROLE_ARN",
    "AWS_ROLE_ID",
    "AWS_ROLE_NAME",
    "AWS_S3_ARN",
    "AWS_S3_BUCKET_NAME",
    "AWS_USER_ARN",
    "AWS_USER_ID",
    "AWS_USER_IDENTITY",
    "AWS_USER_NAME",
    # Cisco
    "CISCO_SECURE_MALWARE_ANALYTICS_SAMPLE_ID",
    # CrowdStrike
    "CROWDSTRIKE_ACCOUNT_ID",
    "CROWDSTRIKE_ALERT_ID",
    "CROWDSTRIKE_ASSET_ID",
    "CROWDSTRIKE_BEHAVIOR_ID",
    "CROWDSTRIKE_CUSTOMER_ID",
    "CROWDSTRIKE_DETECTION_ID",
    "CROWDSTRIKE_DEVICE_ID",
    "CROWDSTRIKE_GROUP_ID",
    "CROWDSTRIKE_INCIDENT_ID",
    "CROWDSTRIKE_INDICATOR_ID",
    "CROWDSTRIKE_PROCESS_ID",
    "CROWDSTRIKE_SIEM_LOGON_EVENT",
    "CROWDSTRIKE_SIEM_SCHEDULED_TASK_EVENT",
    "CROWDSTRIKE_USER_ID",
    "CROWDSTRIKE_USER_ROLE_ID",
    # Expel
    "EXPEL_WORKBENCH_ALERT_ID",
    "EXPEL_WORKBENCH_INVESTIGATION_ID",
    # Flashpoint
    "FLASHPOINT_USER_NAME",
    # FortiDLP
    "FORTIDLP_AGENT_ID",
    "FORTIDLP_CASE_ID",
    "FORTIDLP_INCIDENT_ID",
    "FORTIDLP_OPERATOR_ID",
    "FORTIDLP_SENSOR_EVENT_ID",
    "FORTIDLP_SESSION_ID",
    "FORTIDLP_USER_ID",
    # GPG
    "GPG_KEY_ID",
    "GPG_PUBLIC_KEY_BLOCK",
    "GPG_PUBLIC_KEY_FINGERPRINT",
    # GitHub
    "GITHUB_ACCESS_TOKEN_HASH",
    "GITHUB_COMMIT_SHA",
    "GITHUB_REPOSITORY_BRANCH_NAME",
    "GITHUB_REPOSITORY_FULL_NAME",
    "GITHUB_REPOSITORY_NAME",
    "GITHUB_SAML_IDENTITY",
    "GITHUB_USER_ID",
    "GITHUB_USERNAME",
    # Microsoft 365 / Defender / Entra
    "MESSAGE_TRACE_ID",
    "MICROSOFT_365_AUDIT_LOGGING_VERIFICATION",
    "MICROSOFT_365_DEFENDER_ADVANCED_HUNTING_EXCHANGE_EMAIL_EVENT",
    "MICROSOFT_365_DEFENDER_ADVANCED_HUNTING_SHAREPOINT_EVENT",
    "MICROSOFT_365_DEFENDER_INCIDENT_ID",
    "MICROSOFT_365_EMAIL_CLUSTER_ID",
    "MICROSOFT_365_EXCHANGE_IDENTITY",
    "MICROSOFT_365_EXCHANGE_INBOX_RULE_ID",
    "MICROSOFT_365_EXCHANGE_TRANSPORT_RULE_IDENTITY",
    "MICROSOFT_365_GROUP_SID",
    "MICROSOFT_365_MAILBOX_AUDITING_VERIFICATION",
    "MICROSOFT_365_MAILBOX_GUID",
    "MICROSOFT_365_MESSAGE_ID",
    "MICROSOFT_365_NETWORK_MESSAGE_ID",
    "MICROSOFT_365_SECURITY_AND_COMPLIANCE_ALERT_ID",
    "MICROSOFT_365_SESSION_ID",
    "MICROSOFT_365_SHAREPOINT_LISTITEMUNIQUEID",
    "MICROSOFT_365_SHAREPOINT_SITE_GUID",
    "MICROSOFT_DEFENDER_FOR_CLOUD_APPS_ALERT_ID",
    "MICROSOFT_DEFENDER_FOR_CLOUD_APPS_BEHAVIOR_ID",
    "MICROSOFT_DEFENDER_FOR_ENDPOINT_ALERT_ID",
    "MICROSOFT_DEFENDER_FOR_ENDPOINT_LOGON_ID",
    "MICROSOFT_DEFENDER_FOR_ENDPOINT_MACHINE_ID",
    "MICROSOFT_DEFENDER_FOR_ENDPOINT_PROCESS_UNIQUE_ID",
    "MICROSOFT_DEFENDER_FOR_ENDPOINT_USER_NAME",
    "MICROSOFT_DEFENDER_FOR_IDENTITY_ALERT_ID",
    "MICROSOFT_DEFENDER_FOR_OFFICE_365_ALERT_ID",
    "MICROSOFT_DEFENDER_FOR_OFFICE_365_USER_SUBMISSION_ALERT_ID",
    "MICROSOFT_DEFENDER_SOFTWARE_NAME",
    "MICROSOFT_DEFENDER_VULNERABILITY_ID",
    "MICROSOFT_ENTRA_ADMINISTRATION_UNIT_ID",
    "MICROSOFT_ENTRA_ADMINISTRATIVE_UNIT_ID",
    "MICROSOFT_ENTRA_ADVANCED_AUDIT_VERIFICATION",
    "MICROSOFT_ENTRA_APPLICATION_ID",
    "MICROSOFT_ENTRA_CONDITIONAL_ACCESS_POLICY_ID",
    "MICROSOFT_ENTRA_DEVICE_ID",
    "MICROSOFT_ENTRA_DEVICE_OBJECT_ID",
    "MICROSOFT_ENTRA_DISPLAY_NAME",
    "MICROSOFT_ENTRA_GROUP_ID",
    "MICROSOFT_ENTRA_OBJECT_ID",
    "MICROSOFT_ENTRA_PREMIUM_VERIFICATION",
    "MICROSOFT_ENTRA_RESOURCE_ID",
    "MICROSOFT_ENTRA_ROLE_ID",
    "MICROSOFT_ENTRA_SECURITY_ALERT_ID",
    "MICROSOFT_ENTRA_SERVICE_PRINCIPAL_ID",
    "MICROSOFT_ENTRA_SIGNIN_CORRELATION_ID",
    "MICROSOFT_ENTRA_TENANT_ID",
    "MICROSOFT_ENTRA_USER_AUTOMATIC_REPLY_SETTINGS",
    "MICROSOFT_ENTRA_USER_MAILBOX_AUDITING_VERIFICATION",
    "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME",
    "MICROSOFT_EXCHANGE_DISTRIBUTION_GROUP_IDENTITY",
    # NextDLP
    "NEXTDLP_AGENT_ID",
    "NEXTDLP_CASE_ID",
    "NEXTDLP_INCIDENT_ID",
    "NEXTDLP_OPERATOR_ID",
    "NEXTDLP_SENSOR_EVENT_ID",
    "NEXTDLP_SESSION_ID",
    "NEXTDLP_USER_ID",
    # Okta
    "OKTA_APP_INSTANCE_ID",
    "OKTA_APPKEY_ID",
    "OKTA_APPLICATION_ID",
    "OKTA_CLIENT_ID",
    "OKTA_CREDENTIAL",
    "OKTA_DEVICE_ID",
    "OKTA_EXTERNAL_IDP_USER_ID",
    "OKTA_FACTOR_ID",
    "OKTA_GRANT_ID",
    "OKTA_GROUP_ID",
    "OKTA_IDP_ID",
    "OKTA_IDP_KEY_ID",
    "OKTA_IDENTITY_THREAT_PROTECTION_EVENT",
    "OKTA_KEY_CREDENTIAL_ID",
    "OKTA_POLICY_ID",
    "OKTA_POLICYMAPPING_ID",
    "OKTA_POLICYRULE_ID",
    "OKTA_PROFILEMAPPING_ID",
    "OKTA_ROLE_ID",
    "OKTA_SECURITY_THREAT",
    "OKTA_SYSTEM_LOG_EVENT_ID",
    "OKTA_TOKEN_ID",
    "OKTA_TRANSACTION_ID",
    "OKTA_USER_CREDENTIALS",
    "OKTA_USER_ID",
    "OKTA_USER_LOGIN",
    "OKTA_USER_REPORTED_SUSPICIOUS_SECURITY_NOTIFICATION",
    "OKTA_USERTYPE_ID",
    # Palo Alto
    "PALO_ALTO_CORTEX_AGENT_ID",
    "PALO_ALTO_CORTEX_ALERT_ID",
    "PALO_ALTO_CORTEX_INCIDENT_ID",
    "PALO_ALTO_CORTEX_XDR_EVENT_ID",
    # Proofpoint
    "PROOFPOINT_ACTOR_ID",
    "PROOFPOINT_CAMPAIGN_ID",
    "PROOFPOINT_MALWARE_ID",
    "PROOFPOINT_TECHNIQUE_ID",
    "PROOFPOINT_THREAT_FAMILY_ID",
    "PROOFPOINT_THREAT_ID",
    # ReversingLabs
    "REVERSINGLABS_DOMAIN_REPORT",
    "REVERSINGLABS_IP_REPORT",
    "REVERSINGLABS_URL_REPORT",
    # SentinelOne
    "SENTINELONE_ACCOUNT_ID",
    "SENTINELONE_ACTIVITY_ID",
    "SENTINELONE_AGENT_ID",
    "SENTINELONE_AGENT_UUID",
    "SENTINELONE_ALERT_ID",
    "SENTINELONE_FILE_EVENT",
    "SENTINELONE_GROUP_ID",
    "SENTINELONE_IP_EVENT",
    "SENTINELONE_MARKETPLACE_APP_ID",
    "SENTINELONE_PROCESS_UNIQUE_ID",
    "SENTINELONE_ROLE_ID",
    "SENTINELONE_SCHEDULED_TASK_EVENT",
    "SENTINELONE_SITE_ID",
    "SENTINELONE_THREAT_EVENT_ID",
    "SENTINELONE_THREAT_ID",
    "SENTINELONE_USER_ID",
    # ServiceNow
    "SERVICENOW_INCIDENT_NUMBER",
    "SERVICENOW_USER_NAME",
    # SharePoint
    "SHAREPOINT_FILE_DOWNLOADED",
    "SHAREPOINT_FILE_EVENT",
    "SHAREPOINT_LISTITEM_UNIQUEID",
    "SHAREPOINT_SHARING_EVENT",
    "SHAREPOINT_STANDARD_EVENT",
    # SpurContext / SpyCloud
    "SPUR_CONTEXT_IP_TAG",
    "SPYCLOUD_BREACH_ID",
    "SPYCLOUD_WATCHLIST_ALERT",
    # VirusTotal
    "VIRUSTOTAL_DOMAIN_SCAN_RESULTS",
    "VIRUSTOTAL_FILE_SCAN_RESULTS",
    "VIRUSTOTAL_IP_SCAN_RESULTS",
    "VIRUSTOTAL_URL_SCAN_RESULTS",
    # Zscaler
    "ZSCALER_CUSTOMER_ID",
    "ZSCALER_DEVICE_ID",
    "ZSCALER_IDENTITY_PROVIDER_NAME",
    "ZSCALER_INTERNET_ACCESS_URL_CATEGORY_NAME",
    "ZSCALER_PRIVATE_ACCESS_APPLICATION_ID",
    "ZSCALER_PRIVATE_ACCESS_APPLICATION_NAME",
    "ZSCALER_PRIVATE_ACCESS_DEVICE_POSTURE_PROFILE_ID",
    "ZSCALER_PRIVATE_ACCESS_IDENTITY_PROVIDER_ID",
    "ZSCALER_PRIVATE_ACCESS_SESSION_ID",
    "ZSCALER_ROLE_ID",
    "ZSCALER_USER_ID",
    "ZSCALER_USER_NAME",
    "ZSCALER_USERNAME",
})

# ---------------------------------------------------------------------------
# Schema definitions
# alertType → list of TypeAnnotation dicts
# ---------------------------------------------------------------------------

SCHEMAS: dict[str, list[dict] | None] = {
    "SplunkES:Access - Brute Force Access Behavior Detected - Rule": [
        {"path": "rule_title",        "type": "ALERT_TITLE"},
        {"path": "rule_description",  "type": "ALERT_DESCRIPTION"},
        {"path": "event_id",          "type": "ALERT_ID"},
        {"path": "_time",             "type": "ALERT_TIME"},
        {"path": "user",              "type": "USER"},
        {"path": "src",               "type": "IP_ADDRESS"},
        {"path": "dest",              "type": "HOST_NAME"},
    ],
    "SplunkES:Endpoint - Recurring Malware Infection - Rule": [
        {"path": "rule_title",        "type": "ALERT_TITLE"},
        {"path": "rule_description",  "type": "ALERT_DESCRIPTION"},
        {"path": "event_id",          "type": "ALERT_ID"},
        {"path": "_time",             "type": "ALERT_TIME"},
        {"path": "dest",              "type": "HOST_NAME"},
        {"path": "user",              "type": "USER"},
        {"path": "file_name",         "type": "FILE_NAME"},
        {"path": "file_hash",         "type": "SHA_256"},
    ],
    "SplunkES:Intrusion Detection - Attack Detected - Rule": [
        {"path": "rule_title",        "type": "ALERT_TITLE"},
        {"path": "rule_description",  "type": "ALERT_DESCRIPTION"},
        {"path": "event_id",          "type": "ALERT_ID"},
        {"path": "_time",             "type": "ALERT_TIME"},
        {"path": "src_ip",            "type": "IP_ADDRESS"},
        {"path": "dest_ip",           "type": "IP_ADDRESS"},
        {"path": "dest",              "type": "HOST_NAME"},
    ],
    # None = allow this alert type but let C0 auto-schema infer the observables.
    # Use this when you want a rule forwarded to C0 without defining a schema manually.
    "SplunkES:Web - Abnormally High Number of HTTP Method Events By Src - Rule": None,
}

# ---------------------------------------------------------------------------
# Validate at import time
# ---------------------------------------------------------------------------

def _validate_schemas() -> None:
    for alert_type, annotations in SCHEMAS.items():
        if annotations is None:
            continue  # auto-schema entry — nothing to validate
        for annotation in annotations:
            t = annotation.get("type", "")
            if t not in VALID_C0_TYPES:
                warnings.warn(
                    f"schemas.py: '{t}' in schema for '{alert_type}' is not a valid "
                    f"C0 lead type — submission will be rejected with 400",
                    stacklevel=2,
                )

_validate_schemas()


def is_allowed(alert_type: str) -> bool:
    """Return True if this alert type is in the allow-list (regardless of whether a schema is defined)."""
    return alert_type in SCHEMAS


def get_schema(alert_type: str) -> list[dict] | None:
    """Return the TypeAnnotation list for the given alertType, or None if not found or auto-schema."""
    return SCHEMAS.get(alert_type)
