// Azure Bicep template for Document Archive with Blob Storage

param location string = resourceGroup().location
param environment string = 'dev'
param storageAccountName string = 'docarchive${uniqueString(resourceGroup().id)}'
param containerName string = 'document-archive'
param createIcebergWarehouse bool = false

// Storage Account for Document Archive
resource storageAccount 'Microsoft.Storage/storageAccounts@2021-09-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_GRS'  // Geo-redundant storage
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'  // Change to 'Deny' for strict security
    }
  }
  tags: {
    application: 'DocumentArchive'
    environment: environment
  }
}

// Enable versioning
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-09-01' = {
  name: '${storageAccount.name}/default/${containerName}'
  properties: {
    publicAccess: 'None'
  }
}

// Lifecycle Management Policy
resource storageAccountBlobService 'Microsoft.Storage/storageAccounts/blobServices@2021-09-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    isVersioningEnabled: true
    deleteRetentionPolicy: {
      enabled: true
      days: 30
    }
  }
}

// Management Policy for tiering
resource managementPolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2021-09-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'TransitionToCool'
          enabled: true
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [
                'blockBlob'
              ]
            }
            actions: {
              baseBlob: {
                tierToCool: {
                  daysAfterModificationGreaterThan: 30
                }
              }
              snapshot: {
                tierToCool: {
                  daysAfterModificationGreaterThan: 30
                }
              }
            }
          }
        }
        {
          name: 'TransitionToArchive'
          enabled: true
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [
                'blockBlob'
              ]
            }
            actions: {
              baseBlob: {
                tierToArchive: {
                  daysAfterModificationGreaterThan: 365
                }
              }
              snapshot: {
                tierToArchive: {
                  daysAfterModificationGreaterThan: 365
                }
              }
            }
          }
        }
        {
          name: 'DeleteOldVersions'
          enabled: true
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [
                'blockBlob'
              ]
            }
            actions: {
              version: {
                delete: {
                  daysAfterCreationGreaterThan: 90
                }
              }
            }
          }
        }
      ]
    }
  }
}

// Optional: Iceberg Warehouse Container
resource icebergContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-09-01' = if (createIcebergWarehouse) {
  parent: storageAccount
  name: 'iceberg-warehouse'
  properties: {
    publicAccess: 'None'
  }
}

// Managed Identity for app access
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2018-11-30' = {
  name: 'DocumentArchiveIdentity'
  location: location
}

// Role Assignment - Storage Blob Data Contributor
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2021-04-01-preview' = {
  scope: storageAccount
  name: guid(storageAccount.id, managedIdentity.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output containerName string = containerName
output containerUrl string = '${storageAccount.properties.primaryEndpoints.blob}${containerName}'
output managedIdentityId string = managedIdentity.id
output managedIdentityClientId string = managedIdentity.properties.clientId
output icebergContainerName string = createIcebergWarehouse ? 'iceberg-warehouse' : ''
