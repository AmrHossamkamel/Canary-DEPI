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
    string(name: 'DOCKERHUB_CREDENTIALS_ID', defaultValue: 'dockerhub-creds', description: 'Jenkins credentials ID for Docker Hub')
  }

  triggers {
    githubPush()
  }

  environment {
    IMAGE_NAME = "${params.IMAGE_NAME}"
    IMAGE_TAG  = "${params.IMAGE_TAG_OVERRIDE?.trim() ? params.IMAGE_TAG_OVERRIDE : env.BUILD_NUMBER}"
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Setup venv & Install Dependencies') {
      when { expression { fileExists('requirements.txt') } }
      steps {
        sh '''
          set -e
          python3 --version
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip
          pip install --no-cache-dir -r requirements.txt
        '''
      }
    }

    stage('Lint') {
      when { expression { fileExists('ruff.toml') || fileExists('.flake8') || fileExists('setup.cfg') } }
      steps {
        sh '''
          set +e
          . .venv/bin/activate 2>/dev/null || true

          if python3 -m ruff --version >/dev/null 2>&1; then
            ruff check
            exit $?
          fi

          if flake8 --version >/dev/null 2>&1; then
            flake8
            exit $?
          fi

          echo "No ruff/flake8 config found or tools not installed. Skipping lint."
          exit 0
        '''
      }
    }

    stage('Test') {
      when { expression { fileExists('tests') || fileExists('pytest.ini') } }
      steps {
        sh '''
          set -e
          mkdir -p reports
          . .venv/bin/activate 2>/dev/null || true
          python3 -m pytest --junitxml=reports/junit.xml
        '''
      }
      post {
        always {
          junit testResults: 'reports/**/*.xml', allowEmptyResults: true
        }
      }
    }

    stage('Build Docker Image') {
      steps {
        script {
          appImage = docker.build("${IMAGE_NAME}:${IMAGE_TAG}")
        }
      }
    }

    stage('Push Image to DockerHub') {
      // بنرفع بس على main عشان ما ترفعش بيلدات تجريبية من فروع تانية
      when {
        expression {
          return env.BRANCH_NAME == 'main' || env.GIT_BRANCH == 'origin/main' || env.GIT_BRANCH == null
        }
      }
      steps {
        script {
          docker.withRegistry('https://index.docker.io/v1/', params.DOCKERHUB_CREDENTIALS_ID) {
            appImage.push("${IMAGE_TAG}")
            appImage.push("latest")
          }
        }
      }
    }

    stage('Deploy with Ansible') {
      // الديبلوي يحصل بعد ال push (وبرضه على main فقط)
      when {
        expression {
          return env.BRANCH_NAME == 'main' || env.GIT_BRANCH == 'origin/main' || env.GIT_BRANCH == null
        }
      }
      steps {
        script {
          def extraVars = "image_name=${IMAGE_NAME} image_tag=${IMAGE_TAG} container_name=canary-depi"
          withCredentials([
            usernamePassword(
              credentialsId: params.DOCKERHUB_CREDENTIALS_ID,
              usernameVariable: 'DOCKERHUB_USERNAME',
              passwordVariable: 'DOCKERHUB_PASSWORD'
            )
          ]) {
            sh """
              ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/deploy.yml \
              -e '${extraVars} dockerhub_username=${DOCKERHUB_USERNAME} dockerhub_password=${DOCKERHUB_PASSWORD}'
            """
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
