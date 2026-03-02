# AI Skills for This Project

## Skill: Rancher API Expert
- You know Rancher v3 API structure: `/v3/clusters`, pagination via `data.pagination.next`, cluster object shape `{id, name, state}`.
- You always use `POST /v3/clusters/{id}?action=generateKubeconfig` (not GET).
- You always extract `response["config"]` from generateKubeconfig response.
- You always build a fresh `{name: id}` map per run, never cache across executions.

## Skill: HashiCorp Vault KV v2
- You know the difference between logical path (`secret/rancher/...`) and API path (`secret/data/rancher/...`).
- You always structure write payloads as `{"data": {...}}`.
- You always handle 404 as "not yet created" — not as an error.
- You always use `X-Vault-Token` header, never `Authorization: Bearer`.

## Skill: Secure Secret Handling
- You immediately recognize hardcoded credentials and replace them with env var references.
- You always use `pydantic.SecretStr` and call `.get_secret_value()` only in HTTP header construction.
- You never suggest storing secrets in code, comments, or config files committed to git.

## Skill: Async Python
- You write idiomatic `asyncio` + `aiohttp` code.
- You use `asyncio.gather()` with `return_exceptions=True` for parallel cluster processing.
- You always use `asyncio.Semaphore` to limit concurrency.
- You always use `async with aiohttp.ClientSession() as session` — never create a new session per request.

## Skill: YAML-aware kubeconfig comparison
- You never compare kubeconfig strings directly with `==`.
- You always normalize via `yaml.safe_load()` before comparison — this strips comments, normalizes whitespace, and canonicalizes key order.
- You treat parse failure of either kubeconfig as "not equal" → trigger update.

## Skill: Structured Logging
- You use `structlog` with bound context loggers: `log = log.bind(cluster=name, env=env)`.
- You log at appropriate levels: `info` for normal flow, `warning` for skips/retries, `error` for failures.
- You never log kubeconfig content, tokens, or full exception tracebacks at `info` level.

## Skill: Robust CI/CD
- You write `Jenkinsfile` using declarative pipeline syntax.
- You always use `withCredentials` — never `environment { TOKEN = credentials(...) }` for secret strings (to avoid env var exposure in logs).
- You always clean workspace in `post { always { cleanWs() } }`.

## Skill: Production-grade Error Handling
- You isolate per-cluster failures: one cluster failing never aborts others.
- You collect all failures and report them in a structured summary at the end.
- You exit with code 1 only if at least one cluster failed — not for "up-to-date" skips.
- You always include cluster name, environment, and error type in failure records.
