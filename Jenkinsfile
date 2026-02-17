pipeline {
    agent any

    environment {
        RANCHER_DEV_BASE_URL  = credentials('rancher_dev_url')
        RANCHER_DEV_TOKEN     = credentials('rancher_dev_token')
        RANCHER_PROD_BASE_URL = credentials('rancher_prod_url')
        RANCHER_PROD_TOKEN    = credentials('rancher_prod_token')
        VAULT_BASE_URL   = credentials('vault_url')
        VAULT_TOKEN      = credentials('vault_token')
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Setup Python') {
            steps {
                sh 'python3 --version'
                sh 'python3 -m venv venv'
                sh '. venv/bin/activate && pip install -U pip'
            }
        }

        stage('Install dependencies') {
            steps { sh '. venv/bin/activate && pip install -e ".[dev]"' }
        }

        stage('Run linters') {
            steps { sh '. venv/bin/activate && ruff check .' }
        }

        stage('Run mypy') {
            steps { sh '. venv/bin/activate && mypy .' }
        }

        stage('Run tests') {
            steps { sh '. venv/bin/activate && pytest' }
        }

        stage('Execute cluster sync') {
            steps { sh '. venv/bin/activate && python -m project.main --config clusters.yaml' }
        }
    }
}

