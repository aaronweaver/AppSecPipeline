node {
        stage("Main build") {

            git url: 'https://github.com/aaronweaver/scanitall.git'

            docker.image('appsecpipeline/base').inside {
              stage("Coding Languages") {
                sh 'launch.py -t cloc -p all -s static LOC="."'
                sh 'cat reports/cloc/*.json'
              }
           }

        }
}
