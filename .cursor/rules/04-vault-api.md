# Vault API (HashiCorp Vault via Jenkins)

## Authentication
All requests MUST include:
```
X-Vault-Token: <VAULT_TOKEN>
Content-Type: application/json
```

## KV v2 Endpoints

### Read Secret
```
GET {VAULT_URL}/v1/{VAULT_KUBECONFIG_PATH}/{cluster_name}
```
Example: `GET http://msk-jen-mas02.megafon.ru/v1/secret/data/rancher/kubeconfig/dev-cluster-01`

Response:
```json
{
  "data": {
    "data": { "kubeconfig": "<yaml string>" },
    "metadata": { "version": 3 }
  }
}
```
Returns 404 if secret does not exist yet → treat as empty, proceed with write.

### Write Secret
```
POST {VAULT_URL}/v1/{VAULT_KUBECONFIG_PATH}/{cluster_name}
Body: { "data": { "kubeconfig": "<yaml string>" } }
```

## Python Patterns
```python
async def read_kubeconfig_from_vault(
    session: aiohttp.ClientSession, vault_url: str, token: str,
    path: str, cluster_name: str
) -> str | None:
    url = f"{vault_url}/v1/{path}/{cluster_name}"
    async with session.get(url, headers={"X-Vault-Token": token}) as resp:
        if resp.status == 404:
            return None
        resp.raise_for_status()
        data = await resp.json()
    return data["data"]["data"].get("kubeconfig")


async def write_kubeconfig_to_vault(
    session: aiohttp.ClientSession, vault_url: str, token: str,
    path: str, cluster_name: str, kubeconfig: str
) -> None:
    url = f"{vault_url}/v1/{path}/{cluster_name}"
    async with session.post(
        url,
        headers={"X-Vault-Token": token},
        json={"data": {"kubeconfig": kubeconfig}},
    ) as resp:
        resp.raise_for_status()
```

## Rules
- You ALWAYS handle `404` from Vault as "secret not yet created" — write unconditionally in this case.
- You ALWAYS use KV v2 path structure: `secret/data/...` for API calls (note: `secret/data/` prefix is part of the API path, not the logical path).
- You NEVER delete existing secrets — only update with new version.
- You ALWAYS log vault path and cluster name (never the token or kubeconfig content).
- You ALWAYS retry on `5xx` responses with 3 attempts, exponential backoff.
