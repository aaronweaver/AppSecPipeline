echo "Keeping it tidy."
docker rmi $(docker images | grep "none" | awk '/ / { print $3 }')
#docker volume rm $(docker volume ls -qf dangling=true)
#docker rmi $(docker images -q)
echo "Building dockers"
docker build --no-cache -f dockers/base/dockerfile-base . -t appsecpipeline/base
docker build --no-cache -f dockers/base/dockerfile-base-tools . -t appsecpipeline/base-tools
docker build --no-cache -f dockers/base/dockerfile-sast . -t appsecpipeline/sast
docker build --no-cache -f dockers/base/dockerfile-node . -t appsecpipeline/node
docker build --no-cache -f dockers/base/dockerfile-ruby . -t appsecpipeline/ruby
docker build --no-cache -f dockers/base/dockerfile-zap . -t appsecpipeline/zap
docker build --no-cache -f pipelines/jenkins/jenkins-local-dockerfile . -t appsecpipeline/jenkins

echo
echo "Command Shortcuts"
echo 'docker run --rm -ti appsecpipeline/base /bin/bash'
echo 'docker run --rm -ti appsecpipeline/base-tools /bin/bash'
echo 'docker run --rm -ti appsecpipeline/sast /bin/bash'
echo 'docker run --rm -ti appsecpipeline/node /bin/bash'
echo 'docker run --rm -ti appsecpipeline/ruby /bin/bash'
echo 'docker run --rm -ti appsecpipeline/zap /bin/bash'
