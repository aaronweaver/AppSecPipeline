# AppSecPipeline

Docker integration with Jenkins Pipeline to automate your application security pipeline.

### Docker Builds

Build the Jenkins Docker

```
docker build -t appsecpipeline/jenkins -f pipelines/jenkins/jenkins-local-dockerfile .
```

Run Jenkins locally on http://localhost:8080

```
docker run --name jenkins -it -p 8080:8080 -p 50000:50000 -v jenkins_home:/var/jenkins_home -v /var/run/docker.sock:/var/run/docker.sock appsecpipeline/jenkins
```

Browse to http://localhost:8080 and configure Jenkins using the wizard. Accept the default plugins and configure a user which will be used later to configure the Jenkins jobs.

Build the AppSec Pipeline Dockers.

```
sh build-dockers.sh
```

Setup your Python Environment for Jenkins Builder, Use the credentials that you setup in the prior step for Jenkins.

```
sh setup.bash
```

### Run an AppSecPipeline Job

If setup ran correctly in Jenkins there will be jobs named AppSec Pipeline in Jenkins.

## Run an AppSecPipeline Job
Rerun or rebuild Jenkins jobs by running jenkins.bash.
