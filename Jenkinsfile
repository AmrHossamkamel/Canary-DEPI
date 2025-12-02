pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '15'))
  }

  parameters {
    string(name: 'IMAGE_NAME', defaultValue: 'amrhossam1/canary-depi', description: 'Docker image repo user/repo')
    string(name: 'IMAGE_TAG_OVERRIDE', defaultValue: '', description: 'Optional image tag override')
  }

  triggers {
    githubPush()
  }

  environment {
    IMAGE_NAME = "${params.IMAGE_NAME}"
    IMAGE_TAG  = "${params.IMAGE_TAG_OVERRIDE ?: env.BUILD_NUMBER}"
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
        sh 'python3 -m ruff --version >/dev/null 2>&1 && ruff check || (flake8 --version >/dev/null 2>&1 && flake8 || true)'
      }
    }

    stage('Test') {
      when { expression { fileExists('tests') || fileExists('pytest.ini') } }
      steps {
        sh 'mkdir -p reports'
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
          docker.build("${IMAGE_NAME}:${IMAGE_TAG}")
        }
      }
    }

    stage('Push Image') {
      when {
        anyOf {
          branch 'main'
          expression { env.BRANCH_NAME == 'main' || env.GIT_BRANCH == 'origin/main' }
        }
      }
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
      script {
        if (env.WORKSPACE) {
          cleanWs()
          sh 'docker image prune -f || true'
        } else {
          echo 'Skipping cleanup: no workspace allocated (build aborted before node)'
        }
      }
    }
  }
}

