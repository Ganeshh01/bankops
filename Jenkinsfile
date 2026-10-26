
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
    }

    environment {
        IMAGE_NAME = 'bankops-api'
        IMAGE_TAG = 'ci'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh '''
                    set -eu
                    echo "Repository checked out successfully"
                    git rev-parse --short HEAD
                    ls -la
                '''
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                    set -eu
                    python3 --version
                    python3 -m venv .venv-ci
                    .venv-ci/bin/python -m pip install --upgrade pip
                    .venv-ci/bin/python -m pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    set -eu
                    .venv-ci/bin/python -m pytest -v
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu
                    docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .
                    docker image inspect "${IMAGE_NAME}:${IMAGE_TAG}" \
                        --format='Built image: {{.RepoTags}}'
                '''
            }
        }
    }

    post {
        success {
            echo 'BankOps CI pipeline completed successfully.'
        }
        failure {
            echo 'BankOps CI pipeline failed. Review the stage logs.'
        }
        always {
            echo 'BankOps CI pipeline execution finished.'
        }
    }
}
