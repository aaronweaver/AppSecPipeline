echo "Keeping it tidy."
docker rmi $(docker images | grep "none" | awk '/ / { print $3 }')
echo "Building docker"
docker build -f dockers/base/dockerfile . -t appsecpipeline/base
