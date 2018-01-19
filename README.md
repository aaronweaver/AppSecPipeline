# AppSecPipeline

Docker integration with Jenkins Pipeline to automate your application security pipeline.

### AppSecPipeline Command Line

set python path:
```
export PYTHONPATH=/path/to/AppSecPipeline/:$PYTHONPATH
```

Run an nmap scan:
```
cd /pipelines/docker-native/
python docker-native.py -p nmap TARGET=bodgeit -v /tmp/AppSecPipelineReports:/opt/appsecpipeline/ -r /tmp/appsecpipeline/
```

### Docker Build

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

### Docker Compose

The docker compose environment sets up Jenkins based off the Jenkins build above, DefectDojo and the BodgeIt app for testing the tools.

```
cd dockers/appsecpipeline
launchenv.sh
```
Accessing from local machine:

DefectDojo: http://localhost:8000
BodgeIt: http://localhost:9000/bodgeit
Jenkins: http://localhost:8080

Accessing from docker container:

DefectDojo: http://defectdojo.appsec.pipeline:8000
BodgeIt: http://bodgeit.appsec.pipeline:9000/bodgeit
Jenkins: http://jenkins.appsec.pipeline:8080

Startup a docker tool for testing purposes:

```
docker run --rm --name appsecpipeline -it --network=appsecpipeline_default -v ${PWD}/tools:/usr/bin/appsecpipeline/tools -v ${PWD}/controller/:/usr/bin/appsecpipeline  -v appsecpipeline:/var/appsecpipeline appsecpipeline/base-tools /bin/bash
```
Deleting containers
```
docker system prune --filter label=appsecpipeline
```

Create a shared report directory
```
docker volume create --name appsecpipeline_local -o type=none -o device=/Users/aweaver/git/AppSecPipelineReports/
```

### Testing the AppSecPipeline

## Running a dynamic scan:
```
export DOJO_HOST=http://defectdojo.appsec.pipeline:8000
export DOJO_API_KEY=<user_id>:<guid>
export DOJO_PRODUCT_ID=1

cd pipelines/docker-native
python docker-native.py URL=http://bodgeit.appsec.pipeline:8080/bodgeit LOC=. DOJO_HOST=$DOJO_HOST DOJO_API_KEY=$DOJO_API_KEY DOJO_PRODUCT_ID=$DOJO_PRODUCT_ID -p dynamic -v /Users/aweaver/git/AppSecPipelineReports
```

## Running a static scan:
```
export DOJO_HOST=http://defectdojo.appsec.pipeline:8000
export DOJO_API_KEY=<user_id>:<guid>
export DOJO_PRODUCT_ID=1
export SNYK_API_TOKEN=<api_token>

#Git clone a repo, for example:
git clone https://github.com/psiinon/bodgeit.git

cd pipelines/docker-native
python docker-native.py LOC=. DOJO_HOST=$DOJO_HOST DOJO_API_KEY=$DOJO_API_KEY DOJO_PRODUCT_ID=$DOJO_PRODUCT_ID -p static -v /Path/To/Source Code/
```
