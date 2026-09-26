pipeline {
    agent any
    environment {
        PATH = "/home/linuxbrew/.linuxbrew/bin:${env.PATH}"
    }
    triggers {
        pollSCM('* * * * *')
    }

    stages {
        stage('Installing Tools') {
            steps {
                sh '''
                    set -eu

                    apt-get update
                    DEBIAN_FRONTEND=noninteractive apt-get install -y ruby-full git

                    ruby --version
                    gem --version
                '''
            }
        }
        stage('Installing Kamal'){
            steps{
                sh 'apt-get --version'
                sh 'gem install kamal'
                sh 'kamal --version'
            }
        }
        stage('Tests') {
            agent {
                docker {
                    image 'python:3.12-slim'
                    reuseNode true
                }
            }
            steps {
                sh 'python --version'

                sh '''
                    python -m pip install --upgrade pip
                    python -m pip install uv

                    uv --version
                    uv sync
                    uv run pytest -v
                    ls -lsa
                '''
            }
        }
//         stage('Code Quality') {
//           agent {
//             docker {
//               image 'ghcr.io/astral-sh/uv:python3.13-bookworm-slim'
//               reuseNode true
//             }
//           }
//           steps {
//             sh '''
//               uv sync --frozen
//               uv run ruff check .
//               uv run ruff format --check .
//             '''
//           }
//         }
        stage('Code Quality') {
            agent {
                docker {
                    image 'python:3.12-slim'
                    reuseNode true
                }
            }

            steps {
                sh '''
                    python -m pip install uv

                    echo "Scanning Python source code..."

                    uvx --from 'bandit[toml]' bandit -c pyproject.toml -r .

                    echo "Scanning dependencies..."
                    uv export --frozen --no-hashes --no-emit-project --output-file requirements-audit.txt
                    uvx pip-audit -r requirements-audit.txt
                '''
            }
        }


        stage('Security Analysis') {
            steps {
                withSonarQubeEnv('SonarCloud') {
                    sh "${tool 'sonar-scanner'}/bin/sonar-scanner"
                }
            }
        }
        stage('Deploy') {
          when { branch 'main' }
          steps {
            sshagent(credentials: ['droplet-ssh']) {
              withCredentials([usernamePassword(credentialsId: 'ghcr-token',
                                                usernameVariable: 'KAMAL_REGISTRY_USERNAME',
                                                passwordVariable: 'KAMAL_REGISTRY_PASSWORD')]) {
                sh '''
                  git branch -f jenkins-deploy HEAD
                  kamal deploy
                '''
              }
            }
          }
        }
    }
}