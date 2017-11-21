echo
echo "Updating Jenkins Jobs"
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/arachni-dojo.yaml
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/nikto-arachni-parallel.yaml
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/bodge-it.yaml
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/retirejs.yaml
