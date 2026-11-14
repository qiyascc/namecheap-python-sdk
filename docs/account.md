# Account balance

The client itself has one method that is not about a domain: `balances()`.

```python
from namecheap_sdk import Namecheap

with Namecheap() as nc:
    b = nc.balances()
    print(b.available, b.currency)
```

It returns a {py:class}`~namecheap_sdk.Balances`:

| Field | Meaning |
| --- | --- |
| `currency` | For example `USD`. |
| `available` | Money you can spend now. |
| `account` | The account balance. |
| `earned` | Earned amount, for affiliate and reseller accounts. |
| `withdrawable` | What can be paid out. |
| `required_for_auto_renew` | What the coming auto renewals will need. |

Every amount is a `Decimal`, or `None` if Namecheap left it out.

## Two uses

**Checking credentials.** `balances()` is a cheap call that touches no domain, so it is a good first call to see whether the API user, key and whitelisted IP work together. See [](credentials.md#check-that-it-works).

**Warning before renewals fail.** If the balance is below what the auto renewals need, renewals can fail and domains can lapse. A small scheduled script catches that early:

```python
from namecheap_sdk import Namecheap

with Namecheap() as nc:
    b = nc.balances()
    if b.available is not None and b.required_for_auto_renew is not None:
        if b.available < b.required_for_auto_renew:
            short = b.required_for_auto_renew - b.available
            print(f"Top up {short} {b.currency} before the next renewals")
```

Run it weekly with [](examples/scheduled-jobs.md), and send the output to yourself by mail or chat.

On the async client, await it: `await nc.balances()`.
