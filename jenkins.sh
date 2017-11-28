echo
echo "Updating Jenkins Jobs"
#For some reason specifying * in the directory doesn't work
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/arachni-dojo.yaml
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/nikto-arachni-parallel.yaml
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/bodge-it.yaml
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/retirejs.yaml
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/brakeman.yaml
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/synk.yaml
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/dynamic-pipeline.yaml
