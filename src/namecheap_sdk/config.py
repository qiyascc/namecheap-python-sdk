from __future__ import annotations

from typing import Any, Optional

from goodconf import Field, GoodConf, GoodConfConfigDict
from pydantic import BaseModel, SecretStr

from ._version import __version__
from .errors import AuthenticationError
from .messages import text


class Commands(BaseModel):
    get_hosts: str = "namecheap.domains.dns.getHosts"
    set_hosts: str = "namecheap.domains.dns.setHosts"
    get_nameservers: str = "namecheap.domains.dns.getList"
    set_custom_nameservers: str = "namecheap.domains.dns.setCustom"
    set_default_nameservers: str = "namecheap.domains.dns.setDefault"
    list_domains: str = "namecheap.domains.getList"
    domain_info: str = "namecheap.domains.getInfo"
    check: str = "namecheap.domains.check"
    tlds: str = "namecheap.domains.getTldList"
    get_lock: str = "namecheap.domains.getRegistrarLock"
    set_lock: str = "namecheap.domains.setRegistrarLock"
    balances: str = "namecheap.users.getBalances"


class Settings(GoodConf):
    model_config = GoodConfConfigDict(
        env_prefix="NAMECHEAP_",
        file_env_var="NAMECHEAP_CONFIG",
        default_files=["namecheap.toml", "namecheap.yaml", "namecheap.yml", "namecheap.json"],
        extra="ignore",
        env_nested_delimiter="__",
    )

    api_user: str = Field(default="", description=text("settings.api_user"))
    api_key: SecretStr = Field(default=SecretStr(""), description=text("settings.api_key"))
    username: Optional[str] = Field(default=None, description=text("settings.username"))
    client_ip: str = Field(default="", description=text("settings.client_ip"))
    environment: str = Field(default="production", description=text("settings.environment"))
    base_url: Optional[str] = Field(default=None, description=text("settings.base_url"))
    production_url: str = Field(default="https://api.namecheap.com/xml.response",
                                description=text("settings.production_url"))
    sandbox_url: str = Field(default="https://api.sandbox.namecheap.com/xml.response",
                             description=text("settings.sandbox_url"))
    commands: Commands = Field(default_factory=Commands, description=text("settings.commands"))
    timeout: float = Field(default=30.0, gt=0, description=text("settings.timeout"))
    max_retries: int = Field(default=3, ge=0, description=text("settings.max_retries"))
    max_retry_wait: float = Field(default=60.0, ge=0, description=text("settings.max_retry_wait"))
    backoff_base: float = Field(default=1.0, ge=0, description=text("settings.backoff_base"))
    backoff_cap: float = Field(default=16.0, ge=0, description=text("settings.backoff_cap"))
    page_size: int = Field(default=100, ge=10, le=100, description=text("settings.page_size"))
    default_ttl: int = Field(default=1800, ge=60, le=60000, description=text("settings.default_ttl"))
    user_agent: str = Field(default="namecheap-python-sdk/{version}", description=text("settings.user_agent"))

    @property
    def environments(self) -> dict[str, str]:
        return {"production": self.production_url, "prod": self.production_url,
                "sandbox": self.sandbox_url, "test": self.sandbox_url}

    def resolved_base_url(self) -> str:
        if self.base_url:
            return self.base_url
        env = self.environment.strip().lower()
        if env not in self.environments:
            raise ValueError(text("error.unknown_environment", environment=env, choices="production, sandbox"))
        return self.environments[env]

    def command(self, name: str) -> str:
        return str(getattr(self.commands, name))

    def resolved_user_agent(self) -> str:
        return self.user_agent.replace("{version}", __version__)

    def require_credentials(self) -> dict[str, str]:
        user = self.api_user.strip()
        key = self.api_key.get_secret_value().strip()
        ip = self.client_ip.strip()
        if not user or not key or not ip:
            raise AuthenticationError(text("error.missing_credentials"))
        return {"ApiUser": user, "ApiKey": key, "UserName": (self.username or user).strip(), "ClientIp": ip}


Settings.__doc__ = text("settings.description")


def load_settings(config_file: Optional[str] = None, **overrides: Any) -> Settings:
    given = {key: value for key, value in overrides.items() if value is not None}
    return Settings(load=True, config_file=config_file, **given)
