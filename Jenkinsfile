pipeline {
  agent any

  environment {
    STAGING_URL    = 'https://houses-staging.kmaster.app'
    PRODUCTION_URL = 'https://houses.kmaster.app'
    HEALTH_PATH    = '/_stcore/health'
  }

  triggers {
    pollSCM('* * * * *')
  }

  stages {
    // Code Quality Check and Tests share the workspace .venv (reuseNode), so they must
    // use the same Python. A different one makes uv delete and rebuild the whole .venv.
    stage('Code Quality Check') {
      agent {
        docker {
          image 'ghcr.io/astral-sh/uv:python3.13-bookworm-slim'
          reuseNode true
        }
      }
      steps {
        sh '''
          uv sync --locked
          uv run ruff check .
          uv run ruff format --check .
        '''
      }
    }

    stage('Tests') {
      agent {
        docker {
          image 'ghcr.io/astral-sh/uv:python3.13-bookworm-slim'
          reuseNode true
        }
      }
      steps {
        sh '''
          uv sync --locked
          uv run pytest -v
        '''
      }
    }

    stage('Deploy to Staging') {
      when { branch 'main' }
      steps {
        sshagent(credentials: ['droplet-ssh']) {
          withCredentials([usernamePassword(credentialsId: 'ghcr-token',
                                            usernameVariable: 'KAMAL_REGISTRY_USERNAME',
                                            passwordVariable: 'KAMAL_REGISTRY_PASSWORD')]) {
            sh '''
              git branch -f jenkins-deploy HEAD
              kamal deploy -d staging
            '''
          }
        }
      }
    }

    stage('Smoke test Staging') {
      when { branch 'main' }
      steps {
        sh 'curl -fsS --retry 10 --retry-delay 3 --retry-all-errors "$STAGING_URL$HEALTH_PATH"'
      }
    }

    stage('Deploy to Production') {
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

    stage('Smoke test Production') {
      when { branch 'main' }
      steps {
        sh 'curl -fsS --retry 10 --retry-delay 3 --retry-all-errors "$PRODUCTION_URL$HEALTH_PATH"'
      }
    }
  }
}
