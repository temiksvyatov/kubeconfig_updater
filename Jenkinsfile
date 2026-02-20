pipeline {
    agent any

    environment {
        // Corporate Docker registry and image (push image here; adjust to your registry path)
        DOCKER_REGISTRY = 'registry.example.com'
        DOCKER_IMAGE    = 'registry.example.com/your-group/kubeconfig-updater:latest'

        // Default env vars for the app (optional; app has built-in defaults)
        REQUEST_TIMEOUT = '10'
        RETRY_COUNT     = '3'
        LOG_LEVEL       = 'INFO'
        GLOBAL_TIMEOUT  = '600'

        // Rancher and Vault come from Jenkins credentials (do not hardcode secrets)
        RANCHER_DEV_BASE_URL  = credentials('rancher_dev_url')
        RANCHER_DEV_TOKEN     = credentials('rancher_dev_token')
        RANCHER_PROD_BASE_URL = credentials('rancher_prod_url')
        RANCHER_PROD_TOKEN    = credentials('rancher_prod_token')
        VAULT_BASE_URL        = credentials('vault_url')
        VAULT_TOKEN           = credentials('vault_token')
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Run cluster sync') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'docker-registry-credentials',
                    usernameVariable: 'REGISTRY_USER',
                    passwordVariable: 'REGISTRY_PASS'
                )]) {
                    sh '''
                        set -e
                        echo "$REGISTRY_PASS" | docker login -u "$REGISTRY_USER" --password-stdin "$DOCKER_REGISTRY"
                        docker pull "$DOCKER_IMAGE"
                        docker run --rm \
                            -e RANCHER_DEV_BASE_URL \
                            -e RANCHER_DEV_TOKEN \
                            -e RANCHER_PROD_BASE_URL \
                            -e RANCHER_PROD_TOKEN \
                            -e VAULT_BASE_URL \
                            -e VAULT_TOKEN \
                            -e REQUEST_TIMEOUT="$REQUEST_TIMEOUT" \
                            -e RETRY_COUNT="$RETRY_COUNT" \
                            -e LOG_LEVEL="$LOG_LEVEL" \
                            -e GLOBAL_TIMEOUT="$GLOBAL_TIMEOUT" \
                            -v "$WORKSPACE/clusters.yaml:/app/clusters.yaml:ro" \
                            "$DOCKER_IMAGE"
                    '''
                }
            }
        }
    }
}
