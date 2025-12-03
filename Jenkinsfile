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
    string(name: 'DOCKERHUB_CREDENTIALS_ID', defaultValue: 'dockerhub-creds', description: 'Jenkins credentials ID for Docker Hub (optional)')
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

    stage('Deploy with Ansible') {
      steps {
        script {
          def extraVars = "image_name=${IMAGE_NAME} image_tag=${IMAGE_TAG} container_name=canary-depi"
          withCredentials([usernamePassword(credentialsId: params.DOCKERHUB_CREDENTIALS_ID, usernameVariable: 'DOCKERHUB_USERNAME', passwordVariable: 'DOCKERHUB_PASSWORD')]) {
            sh "ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/deploy.yml -e '${extraVars} dockerhub_username=${DOCKERHUB_USERNAME} dockerhub_password=${DOCKERHUB_PASSWORD}'"
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
        } else {
          echo 'Skipping cleanup: no workspace allocated (build aborted before node)'
        }
      }
    }
  }
}

