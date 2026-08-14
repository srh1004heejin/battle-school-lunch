# Azure deployment

The application runs on Azure Container Apps in Korea Central:

- an external frontend Container App
- internal backend and MCP Container Apps connected through service discovery
- Azure Container Registry for the two application images
- local container storage for active SQLite access
- Azure Files mounted at `/app/backend/data` for durable SQLite snapshots

`infra/main.bicep` is deployed in two phases. The first phase creates ACR and
shared infrastructure. After the backend and frontend images are built in ACR,
the second phase creates the Container Apps. `NEIS_API_KEY` and the GitHub token
are secure deployment parameters and become Container Apps secrets.

SQLite cannot safely acquire its file locks on the Azure Files SMB mount. The
backend therefore runs SQLite on local container storage, restores the latest
snapshot at startup, and atomically refreshes the Azure Files snapshot after
each committed analysis. The backend is fixed at one replica to prevent
concurrent snapshot writers.
