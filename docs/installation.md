# Installation

This page takes you from an empty folder to a working import. If you already have a project with its own virtual environment, skip to [Install the package](#install-the-package).

## Requirements

- Python 3.10 or newer. Check with `python --version` (on Windows, `py --version`).
- Network access to the Namecheap API from the machine that runs your code.
- An account with Namecheap and API credentials. Namecheap uses an API user, an API key and a whitelisted IPv4 address. See [](credentials.md).

The package pulls in four dependencies, all installed for you:

| Package | Why it is needed |
| --- | --- |
| [httpx](https://www.python-httpx.org/) | Sends the HTTP requests, both sync and async. |
| [goodconf](https://github.com/lincolnloop/goodconf) | Loads settings from code, environment variables and files. |
| [pydantic](https://docs.pydantic.dev/) | Validates the settings. |
| [PyYAML](https://pyyaml.org/) | Reads the message catalogue and YAML config files. |

## Create a virtual environment

A virtual environment keeps the SDK and its dependencies separate from the Python that came with your system. Create one inside your project folder.

::::{tab-set}

:::{tab-item} Linux and macOS
```bash
mkdir dns-tools
cd dns-tools
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt now starts with `(.venv)`. Run `deactivate` to leave it, and `source .venv/bin/activate` again whenever you open a new terminal.
:::

:::{tab-item} Windows (CMD)
```bat
mkdir dns-tools
cd dns-tools
py -m venv .venv
.venv\Scripts\activate.bat
```

Your prompt now starts with `(.venv)`. Run `deactivate` to leave it, and `.venv\Scripts\activate.bat` again whenever you open a new CMD window.
:::
::::

## Install the package

::::{tab-set}

:::{tab-item} pip
```bash
pip install namecheap-python-sdk
```
:::

:::{tab-item} uv
```bash
uv add namecheap-python-sdk
```

Outside a uv project, `uv pip install namecheap-python-sdk` installs it into the active environment.
:::

:::{tab-item} Poetry
```bash
poetry add namecheap-python-sdk
```
:::
::::

The distribution is called `namecheap-python-sdk`, but you import it as `namecheap_sdk`:

```python
from namecheap_sdk import Namecheap
```

## Optional extras

Configuration files in JSON work out of the box. Two extras add the other formats:

| Extra | Adds | When you need it |
| --- | --- | --- |
| `yaml` | YAML support in goodconf | You keep settings in `namecheap.yaml` or `namecheap.yml`. |
| `toml` | TOML support in goodconf | You keep settings in `namecheap.toml` and run Python 3.10. Python 3.11 and newer read TOML without it. |

```bash
pip install "namecheap-python-sdk[yaml]"
pip install "namecheap-python-sdk[toml]"
pip install "namecheap-python-sdk[yaml,toml]"
```

The quotes stop shells like zsh from treating the square brackets as a pattern.

## Check the install

```bash
python -c "import namecheap_sdk; print(namecheap_sdk.__version__)"
```

It prints the installed version, for example `0.1.0`. A `ModuleNotFoundError` usually means the virtual environment is not active, or the package went into a different Python than the one you are running.

You can also check that the client can be built without touching the network. Building a client only reads the settings, it does not send a request:

```python
from namecheap_sdk import Namecheap

client = Namecheap("api_user", "API_KEY", client_ip="203.0.113.5")
print(client)
```

## Pin the version

The SDK follows semantic versioning. Until 1.0, a minor release (0.1 to 0.2) may change the API, so pin the minor version in applications:

```text
namecheap-python-sdk>=0.1,<0.2
```

## Upgrade

```bash
pip install --upgrade namecheap-python-sdk
```

Read the [changelog](changelog.md) before moving to a new minor version.

## Uninstall

```bash
pip uninstall namecheap-python-sdk
```

This leaves the dependencies (httpx, goodconf, pydantic, PyYAML) in place, since other packages may use them. Delete the `.venv` folder to remove everything at once.

## Install from source

To try the latest code from GitHub, or to work on the SDK itself:

```bash
git clone https://github.com/qiyascc/namecheap-python-sdk.git
cd namecheap-python-sdk
pip install -e ".[dev]"
```

See [](development.md) for running the tests.
