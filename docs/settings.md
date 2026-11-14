# Settings reference

Every setting the client reads, with its environment variable and default. Set them in code, in the environment or in a config file, as described in [](configuration.md).

| Setting | Environment variable | Type | Default | Allowed | Description |
| --- | --- | --- | --- | --- | --- |
| `api_user` | `NAMECHEAP_API_USER` | string | not set |  | Account name that owns the API key. |
| `api_key` | `NAMECHEAP_API_KEY` | secret string | not set |  | API key from Profile, Tools, Namecheap API Access. |
| `username` | `NAMECHEAP_USERNAME` | string | not set |  | Account the commands run on. Defaults to api_user. |
| `client_ip` | `NAMECHEAP_CLIENT_IP` | string | not set |  | Whitelisted IPv4 address of the machine that makes the calls. |
| `environment` | `NAMECHEAP_ENVIRONMENT` | string | `production` |  | Which Namecheap environment to call: production or sandbox. |
| `base_url` | `NAMECHEAP_BASE_URL` | string | not set |  | Full API URL. Overrides the environment when set. |
| `production_url` | `NAMECHEAP_PRODUCTION_URL` | string | `https://api.namecheap.com/xml.response` |  | API URL used for the production environment. |
| `sandbox_url` | `NAMECHEAP_SANDBOX_URL` | string | `https://api.sandbox.namecheap.com/xml.response` |  | API URL used for the sandbox environment. |
| `commands` | `NAMECHEAP_COMMANDS__<NAME>` | table | see below |  | Command names sent for every call. |
| `timeout` | `NAMECHEAP_TIMEOUT` | number | `30` | > 0 | Seconds to wait for a single request. |
| `max_retries` | `NAMECHEAP_MAX_RETRIES` | integer | `3` | >= 0 | How many times a failed request is tried again. |
| `max_retry_wait` | `NAMECHEAP_MAX_RETRY_WAIT` | number | `60` | >= 0 | Longest wait in seconds the client accepts between retries. |
| `backoff_base` | `NAMECHEAP_BACKOFF_BASE` | number | `1` | >= 0 | First backoff delay in seconds, doubled on every retry. |
| `backoff_cap` | `NAMECHEAP_BACKOFF_CAP` | number | `16` | >= 0 | Longest backoff delay in seconds. |
| `page_size` | `NAMECHEAP_PAGE_SIZE` | integer | `100` | >= 10, <= 100 | Domains asked for on every page when listing, between 10 and 100. |
| `default_ttl` | `NAMECHEAP_DEFAULT_TTL` | integer | `1800` | >= 60, <= 60000 | TTL in seconds used for new records when none is given. |
| `user_agent` | `NAMECHEAP_USER_AGENT` | string | `namecheap-python-sdk/{version}` |  | User-Agent header. {version} is replaced with the package version. |

## Commands

Namecheap has a single URL and picks the action from a `Command` parameter. Every command name is a setting. Override one with `NAMECHEAP_COMMANDS__<NAME>`, for example `NAMECHEAP_COMMANDS__GET_HOSTS`.

| Name | Default |
| --- | --- |
| `commands.get_hosts` | `namecheap.domains.dns.getHosts` |
| `commands.set_hosts` | `namecheap.domains.dns.setHosts` |
| `commands.get_nameservers` | `namecheap.domains.dns.getList` |
| `commands.set_custom_nameservers` | `namecheap.domains.dns.setCustom` |
| `commands.set_default_nameservers` | `namecheap.domains.dns.setDefault` |
| `commands.list_domains` | `namecheap.domains.getList` |
| `commands.domain_info` | `namecheap.domains.getInfo` |
| `commands.check` | `namecheap.domains.check` |
| `commands.tlds` | `namecheap.domains.getTldList` |
| `commands.get_lock` | `namecheap.domains.getRegistrarLock` |
| `commands.set_lock` | `namecheap.domains.setRegistrarLock` |
| `commands.balances` | `namecheap.users.getBalances` |

## Files

Without `config_file=`, the client looks for these files in the working directory, in this order, and uses the first one it finds:

- `namecheap.toml`
- `namecheap.yaml`
- `namecheap.yml`
- `namecheap.json`

`NAMECHEAP_CONFIG` points at a file anywhere else.
