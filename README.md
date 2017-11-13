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

Build the AppSec Pipeline Docker

```
sh build.sh
```

### Run an AppSecPipeline Job

Create a Pipeline job in Jenkins that uses one of the .pipeline examples in pipelines/jenkins/
