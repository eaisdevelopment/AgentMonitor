"""Non-secret policy for AgentMonitor-managed Ollama credential lookup."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class EnvAuthorizationPolicyV1:
    """Exact credential-source facts bound into probe authorization lineage."""

    policy_version: Literal["agentmonitor-ollama-env-authorization-v1"]
    file_name: Literal[".env"]
    binding_id_pattern: str
    variable_name_pattern: str
    variable_prefix: Literal["AGENTMONITOR_OLLAMA_API_KEY_AMCB_"]
    value_encoding: Literal["base64_standard_canonical"]
    maximum_token_bytes: int
    maximum_encoded_bytes: int
    allowed_token_bytes: Literal["visible_ascii_0x21_0x7e"]
    maximum_file_bytes: int
    stream_chunk_bytes: int
    required_root_mode: int
    required_file_mode: int
    required_link_count: int
    required_owner: Literal["effective_uid"]
    lock_contract: Literal["InheritedAccountCredentialLockV1"]
    credential_file_contract: Literal["EnvCredentialFileAuthorityV1"]
    store_kind: Literal["managed_env_v1"]
    global_lock_name: Literal[".ollama-env.lock"]
    global_lock_policy: Literal["owner_0600_nlink1_exclusive_inherited"]
    parent_directory_policy: Literal[
        "owner_no_other_write_group_write_residual_accepted"
    ]
    path_resolution: Literal["explicit_absolute_path_pinned_parent_file_fds"]
    reload_policy: Literal["read_each_attempt"]
    core_dump_policy: Literal["rlimit_core_zero"]


ENV_AUTHORIZATION_POLICY_V1 = EnvAuthorizationPolicyV1(
    policy_version="agentmonitor-ollama-env-authorization-v1",
    file_name=".env",
    binding_id_pattern=r"amcb_[0-9a-f]{32}\Z",
    variable_name_pattern=r"AGENTMONITOR_OLLAMA_API_KEY_AMCB_[0-9A-F]{32}\Z",
    variable_prefix="AGENTMONITOR_OLLAMA_API_KEY_AMCB_",
    value_encoding="base64_standard_canonical",
    maximum_token_bytes=4096,
    maximum_encoded_bytes=5464,
    allowed_token_bytes="visible_ascii_0x21_0x7e",
    maximum_file_bytes=64 * 1024,
    stream_chunk_bytes=256,
    required_root_mode=0o700,
    required_file_mode=0o600,
    required_link_count=1,
    required_owner="effective_uid",
    lock_contract="InheritedAccountCredentialLockV1",
    credential_file_contract="EnvCredentialFileAuthorityV1",
    store_kind="managed_env_v1",
    global_lock_name=".ollama-env.lock",
    global_lock_policy="owner_0600_nlink1_exclusive_inherited",
    parent_directory_policy="owner_no_other_write_group_write_residual_accepted",
    path_resolution="explicit_absolute_path_pinned_parent_file_fds",
    reload_policy="read_each_attempt",
    core_dump_policy="rlimit_core_zero",
)
