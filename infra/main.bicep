targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short globally unique suffix containing lowercase letters and numbers.')
@minLength(4)
@maxLength(12)
param resourceToken string

@secure()
@description('NEIS API key used only by the backend container.')
param neisApiKey string

@secure()
@description('GitHub token used by the headless Copilot agent.')
param githubToken string

@description('Create Container Apps after images have been pushed to ACR.')
param deployApps bool = false

var registryName = 'bsl${resourceToken}'
var environmentName = 'bsl-env-${resourceToken}'
var backendAppName = 'bsl-backend-${resourceToken}'
var mcpAppName = 'bsl-mcp-${resourceToken}'
var frontendAppName = 'bsl-web-${resourceToken}'
var storageName = 'bsl${resourceToken}data'
var backendImage = '${registryName}.azurecr.io/backend:latest'
var frontendImage = '${registryName}.azurecr.io/frontend:latest'

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'bsl-logs-${resourceToken}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource analysisShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'analysis-data'
  properties: {
    enabledProtocols: 'SMB'
    shareQuota: 5
  }
}

resource environmentStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: environment
  name: 'analysisdata'
  properties: {
    azureFile: {
      accessMode: 'ReadWrite'
      accountKey: storage.listKeys().keys[0].value
      accountName: storage.name
      shareName: analysisShare.name
    }
  }
}

var registryCredentials = registry.listCredentials()
var containerRegistry = {
  server: registry.properties.loginServer
  username: registryCredentials.username
  passwordSecretRef: 'registry-password'
}

resource mcp 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: mcpAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8001
        transport: 'http'
      }
      registries: [containerRegistry]
      secrets: [
        {
          name: 'registry-password'
          value: registryCredentials.passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp'
          image: backendImage
          command: [
            'python'
            '-m'
            'app.mcp_server'
          ]
          env: [
            {
              name: 'MCP_HOST'
              value: '0.0.0.0'
            }
            {
              name: 'MCP_SERVER_PORT'
              value: '8001'
            }
            {
              name: 'BACKEND_INTERNAL_URL'
              value: 'http://${backendAppName}'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

resource backend 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: backendAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
      }
      registries: [containerRegistry]
      secrets: [
        {
          name: 'registry-password'
          value: registryCredentials.passwords[0].value
        }
        {
          name: 'neis-api-key'
          value: neisApiKey
        }
        {
          name: 'github-token'
          value: githubToken
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          env: [
            {
              name: 'NEIS_API_KEY'
              secretRef: 'neis-api-key'
            }
            {
              name: 'COPILOT_GITHUB_TOKEN'
              secretRef: 'github-token'
            }
            {
              name: 'AGENT_MCP_URL'
              value: 'http://${mcpAppName}/mcp'
            }
            {
              name: 'DATABASE_PATH'
              value: '/tmp/battle-school-lunch/analyses.db'
            }
            {
              name: 'DATABASE_BACKUP_PATH'
              value: '/app/backend/data/analyses.db'
            }
            {
              name: 'GITHUB_COPILOT_TIMEOUT_SECONDS'
              value: '180'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          volumeMounts: [
            {
              mountPath: '/app/backend/data'
              volumeName: 'analysis-data'
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'analysis-data'
          storageName: environmentStorage.name
          storageType: 'AzureFile'
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

resource frontend 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: frontendAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
        allowInsecure: false
      }
      registries: [containerRegistry]
      secrets: [
        {
          name: 'registry-password'
          value: registryCredentials.passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          env: [
            {
              name: 'BACKEND_HOST'
              value: backendAppName
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output registryName string = registry.name
output webUrl string = deployApps ? 'https://${frontend!.properties.configuration.ingress.fqdn}' : ''
