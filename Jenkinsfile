pipeline {
  agent any

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
