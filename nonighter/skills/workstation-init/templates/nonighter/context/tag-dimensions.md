# Tag dimensions — Context

> The dimensions a context card is tagged along, the values in use for each, and how a tag string reads. The authority for what a tag means, and the only place a new dimension or a new value is added. Read before writing a card or searching for one.

A card carries **dimensions with values**, not a list of words. The reason is retrieval: *what models do we have for this client* is a question about two dimensions at once, and a flat list of words can only be scanned. `context/instructions-context.md` §3 states the rule; this file holds the vocabulary.

## The three dimensions

| Dimension | Answers | Example values |
|---|---|---|
| `for` | who or what the material belongs to or serves | a client or counterparty name, the user's own organization, `internal` |
| `work` | the kind of work it serves — what job you would be doing when you need it | `valuation`, `pricing`, `closing`, `reporting`, `recruiting` |
| `kind` | what kind of thing it is | `model`, `deck`, `memo`, `dataset`, `contract`, `template`, `playbook` |

**Three is the whole set until a real question cannot be asked without a fourth.** A dimension nothing queries costs a line on every card forever, and the pressure to add one usually comes from a value that belongs in a dimension that already exists. How current something is, and how much authority it carries, are **card keys** (`vintage`, `authority`) rather than dimensions — they qualify a single item rather than grouping items.

## How a tag string reads

On a card, one line per dimension:

```
for: acme-capital
work: valuation
kind: model
```

A dimension that does not apply is **omitted, never filled with a placeholder** — an empty value in a query is indistinguishable from a wrong one. A dimension may carry more than one value where the material genuinely serves both, comma-separated: `work: valuation, pricing`.

## Values in use

*Empty at install.* Values are added as real material turns up, never invented in advance — a vocabulary written before the material is a guess about a folder nobody has read yet.

**Reuse a value that is already listed rather than coining a synonym.** A vocabulary holding both `valuation` and `valuations` answers neither query, and nothing mechanical will notice: the daily conformance run reports a value this file does not list, which is what makes this list worth keeping current in the same pass that writes the card.

| Dimension | Values | First used |
|---|---|---|
| — | *(nothing yet)* | — |

## Adding a dimension

Only with the user's yes, and only when a question they actually asked cannot be answered by the three above. Record it in the table at the top with what it answers and its first values, then say what it costs: every card written from that point carries the new line, and every card written before it does not — so a query on a new dimension silently misses the older material until a run backfills it.
