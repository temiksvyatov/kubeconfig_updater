# Cursor Commands

## @validate-clusters
**Trigger**: When asked to validate or check `clusters.yaml`  
**Action**: Generate or review `clusters.py::validate_clusters_file()`.  
Ensure it checks: file existence, valid YAML, non-empty lists, string cluster names, no duplicates across dev/prod.

## @update-kubeconfigs
**Trigger**: When asked to implement or review the main sync flow  
**Action**: Implement `sync.py::sync_all()` covering all 4 steps from `05-script-requirements.md`.  
Always include: retry logic, semaphore, per-cluster error isolation, final summary log.

## @rancher-client
**Trigger**: When writing or reviewing Rancher API integration  
**Action**: Implement `rancher.py::RancherClient` as an async context manager with `build_cluster_map()` and `get_kubeconfig()` methods. Verify pagination handling and POST for generateKubeconfig.

## @vault-client
**Trigger**: When writing or reviewing Vault API integration  
**Action**: Implement `vault.py::VaultClient` as async context manager. Verify KV v2 path format, 404 handling, write payload structure.

## @compare-kubeconfigs
**Trigger**: When asked about kubeconfig comparison logic  
**Action**: Implement `utils.py::kubeconfigs_are_equal()` using `yaml.safe_load` normalization. Add edge cases: one is None, one is invalid YAML.

## @write-tests
**Trigger**: When asked to add or review tests  
**Action**: Generate `tests/` covering validate_clusters_file (valid/invalid inputs), kubeconfigs_are_equal (equal, different, None, invalid yaml), sync_cluster (mocked rancher+vault, up-to-date path, update path, rancher error path).

## @jenkinsfile
**Trigger**: When asked to create or review the Jenkins pipeline  
**Action**: Generate `Jenkinsfile` with `withCredentials` block mapping all 5 env vars, `docker build`, `docker run` steps. Include `post { always { cleanWs() } }`.

## @check-security
**Trigger**: Before any PR or review of any file  
**Action**: Scan all files for: hardcoded tokens/URLs, use of `print()`, missing type annotations, `requests` library usage, secrets in logs. Report violations.
