#!/usr/bin/env bash
echo "=================================================================================="
echo "Welcome to the AppSecPipeline! This is a quick script to get you up and running."
echo
echo "Requirements:"
echo "    You'll need the URL to your Jenkins sever, username and password"
echo "=================================================================================="
echo

#Create the config/env files for environment specific configuration
if [[ ! -e pipelines/jenkins/config/env ]]; then
    echo "creating directory"
    mkdir pipelines/jenkins/config/env
fi

#Copy the jenkins configuration file
cp pipelines/jenkins/config/template/jenkins_job.ini.template pipelines/jenkins/config/env/jenkins_job.ini

unset HISTFILE

#read -p "Setting up Jenkins? Not necessary for a local install (y/n): " JENKINS
#if [ $JENKINS == 'y' ]
#then
  read -p "Jenkins Server: (http://jenkins-server:8080): " JENKINSSERVER
  echo $JENKINSSERVER
  read -p "Jenkins Username: " JENKINSUSER
  stty -echo
  read -p "Jenkins Password: " JENKINSPASS; echo
  stty echo

  #OSX uses an older version of sed
  if [ "$(uname)" == "Darwin" ]; then
    #Save the settings in the configuration file
    sed -i "" "s~jenkins-server~$JENKINSSERVER~g" config/env/jenkins_job.ini
    sed -i "" "s/jenkins-builder/$JENKINSUSER/g" config/env/jenkins_job.ini
    sed -i "" "s/jenkins-password/$JENKINSPASS/g" config/env/jenkins_job.ini
    sed -i "" "s/jenkins-password/$JENKINSPASS/g" config/env/jenkins_job.ini
  else
    #Save the settings in the configuration file
    sed -i "s~jenkins-server~$JENKINSSERVER~g" config/env/jenkins_job.ini
    sed -i "s/jenkins-builder/$JENKINSUSER/g" config/env/jenkins_job.ini
    sed -i "s/jenkins-password/$JENKINSPASS/g" config/env/jenkins_job.ini
    sed -i "s/jenkins-password/$JENKINSPASS/g" config/env/jenkins_job.ini
  fi
  echo "Jenkins Builder configuration file created in: pipelines/jenkins/config/jenkins_job.ini"
  echo
#fi

echo "Creating the virtual environment"
#create the virtual environment
virtualenv venv

echo "Activating the virtual environment"
#activate virtual environment
. venv/bin/activate

echo
echo "Installing required packages...."

#install the requirements
pip install -r requirements/requirements.txt

echo "Installing jenkins job builder"
git clone https://github.com/openstack-infra/jenkins-job-builder.git
pip install -e .

echo
echo "Creating Jenkins Jobs"
jenkins-jobs --conf pipelines/jenkins/config/env/jenkins_job.ini  update -r pipelines/jenkins/templates/*.yaml

echo
echo
echo "=============================================================================="
echo "Complete!"
echo "=============================================================================="
echo
