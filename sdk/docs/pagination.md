# Pagination

Every list endpoint returns a result envelope with a `next` cursor:

```json
{
  "investigations": [ ... ],
  "next": "eyJjcmVhdGVkVGltZSI6...",
  "errors": [],
  "warnings": []
}
```

To fetch the next page, pass the `next` value back. An **empty
string** means you've reached the end of the result set.

The SDK wraps this in a lazy iterator so you never see the cursor.

## `PaginatedIterator`

Every `cz.<resource>.list(...)` call returns a `PaginatedIterator[T]`.
Iteration triggers HTTP calls one page at a time:

```python
for inv in cz.investigations.list(filter="severity eq 'high'"):
    process(inv)              # HTTP page-1 fetched on first item
                              # HTTP page-2 fetched after last item of page-1
                              # ...stops when next == ""
```

Or materialize the entire result set into a list:

```python
rows = cz.investigations.list(filter="status eq 'completed'").materialize()
print(len(rows))
```

`materialize()` walks every page in one go. Use sparingly — for
queries that match thousands of investigations this can be slow and
memory-heavy.

## Page size

Pass `limit=N` to control how many items the server returns per page.
Range is **1 to 10000**, default 10000.

```python
# Smaller pages = lower per-request latency, more round trips
for inv in cz.investigations.list(filter="...", limit=100):
    ...
```

## GET vs QUERY

The API exposes the same logical operation under two HTTP methods:

| Method | Where it sends params | Best for |
|---|---|---|
| `GET ?filter=…&limit=…&next=…` | URL query string | normal use; broadest role compatibility |
| `QUERY` (custom verb) | JSON body | filters too long for the URL (~8KB+) |

**The SDK defaults to GET.** Reasons:

1. Some role policies allow `GET /<path>` while rejecting
   `QUERY /<path>`. Defaulting to GET maximizes compatibility.
2. GET responses are cacheable by intermediate proxies; QUERY is not.
3. GET requests show up in standard request logs in a parseable form.

To opt into QUERY for a single call:

```python
cz.investigations.list(
    filter="<a very long filter that would exceed URL length>",
    method="QUERY",
)
```

The same applies to every list method on every resource.

## Stopping early

Iterating breaks out cleanly — the iterator stops fetching once your
loop exits:

```python
for inv in cz.investigations.list(filter="severity eq 'critical'"):
    if inv.created_time < cutoff:
        break          # no further pages are fetched
    process(inv)
```

Use this when you only need recent results.

## Per-call org override

All resource list methods accept `organization_id=` to override the
client's default org. Useful for MSSP iteration:

```python
for org in cz.organizations.list():
    for inv in cz.investigations.list(
        filter="status eq 'pending-review'",
        organization_id=org.id,
    ):
        notify(org, inv)
```

## Catalog is special

`cz.catalog.list(...)` returns a `PaginatedIterator` for shape
consistency, but the catalog endpoint **does not paginate** — every
type comes back in a single response and `next` is always empty. There
is no perf cost; iteration just stops after the first page.

## Total counts

The API does not return a total-count header on list responses. To
count results, materialize and `len()`:

```python
n = sum(1 for _ in cz.investigations.list(filter="severity eq 'high' and status ne 'completed'"))
```

Note that `sum(1 for ...)` is more memory-efficient than `len(list)`
when you only need the count.
