# Changelog

## 0.1.0

First release.

- Sync `Namecheap` and async `AsyncNamecheap` clients for the XML API, production and sandbox
- DNS: hosts, list, exists, add, replace, replace_all, delete (all records of a name or one value)
- DNS shortcuts: point, unpoint, alias, set_txt
- Safe writes on top of `setHosts`: read, change, write back the full list, skip the write when nothing changed, keep the mail setting
- Record helpers for A, AAAA, CNAME, ALIAS, TXT, MX, NS, CAA and Namecheap's URL, URL301 and FRAME records
- Domains: list, iter, get, available, available_many, tlds, nameservers, set_nameservers, use_default_nameservers, is_locked, lock, unlock
- `balances()` for the account balance
- XML errors mapped to typed exceptions with Namecheap's error number, automatic retries for rate limits and server errors
- Configuration through goodconf: code, `NAMECHEAP_*` environment variables or a TOML, YAML or JSON file
- Every user facing message lives in `messages.yaml` and can be overridden at runtime
- Every command name comes from the settings and can be overridden
