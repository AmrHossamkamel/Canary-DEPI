pipeline {
  agent any

  parameters {
    string(name: 'IMAGE_NAME', defaultValue: 'yourdockerusername/myapp', description: 'Docker image repository (e.g., user/repo)')
  }

  triggers {
    githubPush()
  }

  environment {
    IMAGE_NAME = "${params.IMAGE_NAME}"
    IMAGE_TAG  = "${env.BUILD_NUMBER}"
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Install Dependencies') {
      when { expression { fileExists('requirements.txt') } }
      steps {
        sh 'python3 --version || true'
        sh 'pip3 --version || true'
        sh 'pip3 install --no-cache-dir -r requirements.txt'
      }
    }

    stage('Lint') {
      when { expression { fileExists('ruff.toml') || fileExists('.flake8') || fileExists('setup.cfg') } }
      steps {
        sh 'ruff check || flake8 || true'
      }
    }

    stage('Test') {
      when { expression { fileExists('tests') || fileExists('pytest.ini') } }
      steps {
        sh 'pytest --junitxml=reports/junit.xml'
      }
      post {
        always {
          junit 'reports/**/*.xml'
        }
      }
    }

    stage('Build Docker Image') {
      steps {
        script {
          def appImage = docker.build("${IMAGE_NAME}:${IMAGE_TAG}")
          env.APP_IMAGE_ID = appImage.id
        }
      }
    }

    stage('Push Image') {
      when { branch 'main' }
      steps {
        script {
          def appImage = docker.image("${IMAGE_NAME}:${IMAGE_TAG}")
          docker.withRegistry('https://index.docker.io/v1/', 'dockerhub-creds') {
            appImage.push("${IMAGE_TAG}")
            appImage.push('latest')
          }
        }
      }
    }
  }

  post {
    success {
      echo "✅ Build OK. Image: ${IMAGE_NAME}:${IMAGE_TAG}"
    }
    failure {
      echo "❌ Build Failed."
    }
    always {
      cleanWs()
      sh 'docker image prune -f || true'
    }
  }
}

