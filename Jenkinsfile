pipeline {
    agent any
    environment {
        PATH = "/home/linuxbrew/.linuxbrew/bin:${env.PATH}"
    }
    triggers {
        pollSCM('* * * * *')
    }

    stages {
//         stage('Checkout') {
//             steps {
//                 checkout scm
//             }
//         }
        stage('Installing Tools') {
            steps {
                sh '''
                    set -eu

                    apt-get update
                    DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential ruby-full git curl openssh-client

                    ruby --version
                    gem --version
                '''
            }
        }

        stage('Installing Homebrew') {
            steps {
                sh '''
                    set -eu

                    if [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
                        echo "Homebrew is already installed"
                    else
                        echo "Installing Homebrew..."

                        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o /tmp/homebrew-install.sh
                        NONINTERACTIVE=1 /bin/bash /tmp/homebrew-install.sh
                    fi

                    command -v brew
                    brew --version
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
        stage('Security') {
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

        stage('Python Tests') {
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

//         stage('SonarQube analysis') {
//             steps {
//                 withSonarQubeEnv('SonarCloud') {
//                     sh "${tool 'sonar-scanner'}/bin/sonar-scanner"
//                 }
//             }
//         }
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