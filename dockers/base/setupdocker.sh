#Python dependency installs
pip install -U pyyaml
pip install -U requests
pip install -U junit_xml_output
pip install -U defectdojo_api
pip install -U cryptography

mkdir /usr/bin/appsecpipeline/
PATH="/usr/bin/appsecpipeline/tools:${PATH}"

chmod +x /usr/bin/appsecpipeline/tools/launch.py
chmod +x /usr/bin/appsecpipeline/tools/junit.py

useradd -m -d /home/appsecpipline appsecpipline -u 1000
