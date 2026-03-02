# Rancher API

## Authentication
All requests MUST include:
```
Authorization: Bearer <RANCHER_TOKEN>
Content-Type: application/json
```

## Endpoints

### List All Clusters
```
GET /v3/clusters
```
Response: `{ "data": [ { "id": "c-xxxxx", "name": "cluster-name", ... } ] }`

### Generate kubeconfig
```
POST /v3/clusters/{clusterId}?action=generateKubeconfig
```
Response: `{ "config": "<kubeconfig yaml string>" }`

## Cluster → Environment Mapping
`clusters.yaml` declares which clusters belong to `dev` or `prod` environment.  
Dev clusters are fetched from `RANCHER_DEV_URL`, prod clusters from `RANCHER_PROD_URL`.

## Name → ID Mapping Pattern
```python
async def build_cluster_map(session: aiohttp.ClientSession, url: str, token: str) -> dict[str, str]:
    """Returns {cluster_name: cluster_id}"""
    async with session.get(
        f"{url}/v3/clusters",
        headers={"Authorization": f"Bearer {token}"},
        ssl=False,  # internal CA — set ssl=True and provide cert in production
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
    return {c["name"]: c["id"] for c in data["data"]}
```

## Generate kubeconfig Pattern
```python
async def get_kubeconfig_from_rancher(
    session: aiohttp.ClientSession, url: str, token: str, cluster_id: str
) -> str:
    async with session.post(
        f"{url}/v3/clusters/{cluster_id}?action=generateKubeconfig",
        headers={"Authorization": f"Bearer {token}"},
        ssl=False,
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
    return data["config"]
```

## Rules
- You ALWAYS paginate: check `data.pagination.next` and follow until exhausted when listing clusters.
- You ALWAYS use `POST` (not GET) for `generateKubeconfig` action.
- You NEVER cache cluster ID mappings across runs — rebuild mapping fresh each execution.
- If a cluster name from `clusters.yaml` is NOT found in Rancher API response, you ALWAYS raise a descriptive error and abort that cluster (not the whole run).
- You ALWAYS retry failed API calls 3 times with exponential backoff (1s, 2s, 4s).
