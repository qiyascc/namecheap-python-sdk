# API access and the sandbox

Namecheap's API needs three things on every request: your **API user**, your **API key**, and the **IPv4 address** the request comes from, which must be on a whitelist you manage. This page walks through setting all three up.

## 1. Turn on API access

1. Sign in to your Namecheap account.
2. Go to **Profile**, then **Tools**, then **Business & Dev Tools**, and open **Namecheap API Access**.
3. Switch API access on and copy the **API key** shown there.

Namecheap only opens the production API to accounts that meet its requirements, so if every call fails with `AuthenticationError` even though the key is right, check that page first.

The **API user** is your Namecheap user name.

## 2. Whitelist your IP address

Every request carries the caller's address as the `ClientIp` parameter, and Namecheap rejects calls from any address that is not on the whitelist.

1. On the same **Namecheap API Access** page, open the whitelisted IPs section.
2. Add the public IPv4 address of every machine that will call the API: your server, and your own computer while you develop.

Find the public address of a machine with:

```bash
curl https://api.ipify.org
```

Then give the SDK the same address:

```python
from namecheap_sdk import Namecheap

nc = Namecheap("your-user", "API_KEY", client_ip="203.0.113.5")
```

```{note}
`client_ip` must be the address Namecheap sees, which is the public address of your network, not a private one like `192.168.1.20`. If the address of the machine changes, update the whitelist and the setting together.
```

## 3. Try the sandbox first

Namecheap runs a separate sandbox at [sandbox.namecheap.com](https://www.sandbox.namecheap.com) for testing. It is a different site with its own account, its own API key and its own whitelist. Nothing you do there touches real domains.

1. Create an account on the sandbox site.
2. Turn on API access and whitelist your IP there, the same way as above.
3. Point the SDK at it:

```python
nc = Namecheap("sandbox-user", "SANDBOX_KEY", client_ip="203.0.113.5", environment="sandbox")
```

| Environment | `environment=` | API URL |
| --- | --- | --- |
| Production | `production` (or `prod`) | `https://api.namecheap.com/xml.response` |
| Sandbox | `sandbox` (or `test`) | `https://api.sandbox.namecheap.com/xml.response` |

Production is the default. Any other value raises `ValueError` when the client is built. `base_url`, when set, overrides the environment.

## Resellers: acting for another account

Every command runs on the account named in `UserName`. By default that is the API user itself. A reseller acting for a customer sets `username` to the customer's account:

```python
nc = Namecheap("reseller-user", "API_KEY", client_ip="203.0.113.5", username="customer-account")
```

## Where to keep the key

Keep the key out of your source code and out of git.

- In development, environment variables or a `namecheap.toml` file listed in `.gitignore`.
- On a server, the environment of the service (a systemd `EnvironmentFile`, a container secret, your platform's secret store).

The settings store the key as a pydantic `SecretStr`, so printing the settings shows `**********`.

```{warning}
For every command except `setHosts`, the SDK sends the credentials as query parameters, because that is how Namecheap's API takes them. That means the key is part of the request URL. Do not log full request URLs, and be careful with proxies that do.
```

## Check that it works

The account balance is a cheap read that touches no domain:

```python
from namecheap_sdk import AuthenticationError, Namecheap

with Namecheap() as nc:
    try:
        balances = nc.balances()
    except AuthenticationError as exc:
        print("Namecheap refused the credentials:", exc)
    else:
        print("Credentials work. Balance:", balances.available, balances.currency)
```

`AuthenticationError` here usually means one of three things: a wrong user or key, an IP that is not whitelisted, or an account that has no API access yet. The error's `number` and `message` come from Namecheap and say which.

If the user, the key or the client IP is missing entirely, building the client raises `AuthenticationError` before any request, with a message that lists every place the SDK looked.
