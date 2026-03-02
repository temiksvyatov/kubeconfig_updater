pipeline {
    agent any

    stages {
        stage('Build and Run') {
            steps {
                withCredentials([
                    string(credentialsId: 'rancher-dev-url',  variable: 'RANCHER_DEV_URL'),
                    string(credentialsId: 'rancher-prod-url', variable: 'RANCHER_PROD_URL'),
                    string(credentialsId: 'rancher-dev-token', variable: 'RANCHER_DEV_TOKEN'),
                    string(credentialsId: 'rancher-prod-token', variable: 'RANCHER_PROD_TOKEN'),
                    string(credentialsId: 'vault-token',       variable: 'VAULT_TOKEN'),
                ]) {
                    sh '''
                        docker build -t kubeconfig-sync:latest .
                        docker run --rm \
                          -e RANCHER_DEV_URL="$RANCHER_DEV_URL" \
                          -e RANCHER_PROD_URL="$RANCHER_PROD_URL" \
                          -e RANCHER_DEV_TOKEN="$RANCHER_DEV_TOKEN" \
                          -e RANCHER_PROD_TOKEN="$RANCHER_PROD_TOKEN" \
                          -e VAULT_URL="$VAULT_URL" \
                          -e VAULT_TOKEN="$VAULT_TOKEN" \
                          -v "$PWD/clusters.yaml:/app/clusters.yaml:ro" \
                          kubeconfig-sync:latest
                    '''
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}

