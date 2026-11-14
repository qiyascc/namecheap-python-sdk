# Configuration

Settings are loaded with [goodconf](https://github.com/lincolnloop/goodconf). You can set any of them in three places, and mix them freely:

1. **In code**, as arguments to `Namecheap(...)`.
2. **In the environment**, as `NAMECHEAP_*` variables.
3. **In a config file**: TOML, YAML or JSON.

When the same setting is in more than one place, code wins over the environment, and the environment wins over the file. Anything you do not set keeps its default. The full list is on [](settings.md).

## In code

The first two positional arguments are the API user and the API key. `client_ip` and every other setting are keyword arguments:

```python
from namecheap_sdk import Namecheap

nc = Namecheap(
    "your-user",
    "API_KEY",
    client_ip="203.0.113.5",
    environment="sandbox",
    timeout=10,
    default_ttl=600,
)
```

Passing `None` for a setting is the same as not passing it, so the next source is used.

## In the environment

Every setting has a variable named `NAMECHEAP_` plus the setting name in capitals:

```bash
export NAMECHEAP_API_USER=your-user
export NAMECHEAP_API_KEY=your-key
export NAMECHEAP_CLIENT_IP=203.0.113.5
export NAMECHEAP_ENVIRONMENT=production
export NAMECHEAP_DEFAULT_TTL=1800
```

Command names, which are nested, use a double underscore:

```bash
export NAMECHEAP_COMMANDS__GET_HOSTS=namecheap.domains.dns.getHosts
```

## In a config file

With no arguments, the client looks in the current working directory for, in this order:

1. `namecheap.toml`
2. `namecheap.yaml`
3. `namecheap.yml`
4. `namecheap.json`

To load a file from somewhere else, set `NAMECHEAP_CONFIG` or pass `config_file=`:

```python
nc = Namecheap(config_file="/etc/myapp/namecheap.toml")
```

::::{tab-set}

:::{tab-item} TOML
```toml
api_user = "your-user"
api_key = "your-key"
client_ip = "203.0.113.5"
environment = "sandbox"
timeout = 15
default_ttl = 1800
```
:::

:::{tab-item} YAML
```yaml
api_user: your-user
api_key: your-key
client_ip: 203.0.113.5
environment: sandbox
timeout: 15
default_ttl: 1800
```
:::

:::{tab-item} JSON
```json
{
  "api_user": "your-user",
  "api_key": "your-key",
  "client_ip": "203.0.113.5",
  "environment": "sandbox",
  "timeout": 15,
  "default_ttl": 1800
}
```
:::
::::

YAML needs the `yaml` extra, and TOML needs the `toml` extra on Python 3.10. JSON always works. Unknown keys are ignored.

```{warning}
A config file with an API key in it is a secret. Keep it out of git and readable only by the user that runs your code.
```

## Building settings yourself

```python
from namecheap_sdk import Namecheap, load_settings

settings = load_settings("/etc/myapp/namecheap.toml", environment="sandbox")
print(settings.environment, settings.resolved_base_url())

nc = Namecheap(settings=settings)
```

The first argument is the config file (or `None` for the default lookup). Keyword arguments override the file and the environment. Arguments passed next to `settings=` are applied on top of a copy:

```python
nc = Namecheap(settings=settings, timeout=5)
```

## Settings that change behaviour

### `default_ttl`

The TTL, in seconds, for new records when you do not give one. Default `1800`. Namecheap accepts TTLs from 60 to 60000 seconds, and the SDK checks the range before it sends anything. When you replace a record that already exists and pass no TTL, the old record's TTL is kept.

### `page_size`

How many domains to ask for on each page while listing, between 10 and 100. Default `100`, the largest Namecheap allows, which means the fewest requests.

### `username`

The account commands run on. Defaults to `api_user`. Only resellers acting for a customer need to change it, see [](credentials.md#resellers-acting-for-another-account).

## Environments and base URL

`environment` picks the API URL: `production` (alias `prod`) or `sandbox` (alias `test`). The URLs themselves come from `production_url` and `sandbox_url`. `base_url`, when set, beats all of them.

## Commands

Namecheap has a single URL and picks the action from a `Command` parameter. Every command name the SDK sends is a setting, so nothing is fixed in the code:

| Name | Default | Used by |
| --- | --- | --- |
| `get_hosts` | `namecheap.domains.dns.getHosts` | `dns.hosts`, `dns.list`, `dns.exists`, and the read step of every write |
| `set_hosts` | `namecheap.domains.dns.setHosts` | every DNS write |
| `get_nameservers` | `namecheap.domains.dns.getList` | `domains.nameservers` |
| `set_custom_nameservers` | `namecheap.domains.dns.setCustom` | `domains.set_nameservers` |
| `set_default_nameservers` | `namecheap.domains.dns.setDefault` | `domains.use_default_nameservers` |
| `list_domains` | `namecheap.domains.getList` | `domains.list`, `domains.iter` |
| `domain_info` | `namecheap.domains.getInfo` | `domains.get` |
| `check` | `namecheap.domains.check` | `domains.available`, `domains.available_many` |
| `tlds` | `namecheap.domains.getTldList` | `domains.tlds` |
| `get_lock` | `namecheap.domains.getRegistrarLock` | `domains.is_locked` |
| `set_lock` | `namecheap.domains.setRegistrarLock` | `domains.lock`, `domains.unlock` |
| `balances` | `namecheap.users.getBalances` | `balances` |

## How requests are sent

Every command except `setHosts` is sent as a `GET` with all parameters in the query string. `setHosts`, which carries the whole zone, is sent as a `POST` with a form body. In both cases the credentials (`ApiUser`, `ApiKey`, `UserName`, `ClientIp`) travel as parameters, as Namecheap expects.

## User agent

Every request carries `User-Agent: namecheap-python-sdk/<version>`. Change it with `user_agent`; `{version}` is replaced with the package version.

## Reading the active settings

```python
nc = Namecheap()
print(nc)
print(nc.settings.default_ttl, nc.settings.page_size)
```

```text
Namecheap(environment='production', base_url='https://api.namecheap.com/xml.response')
1800 100
```
