import argparse
from appsecpipeline import pipeline

if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)

    #Command line options
    parser.add_argument("-p", "--profile", help="The pipeline profile to run from master.yaml", required=True)
    parser.add_argument("-a", "--auth", help="Tool configuration credentials and or API keys.", default=False)
    parser.add_argument("-k", "--key", help="Key file for auth credentials.", default=False)
    parser.add_argument("-d", "--dir", help="Directory to include in docker scan. (Copies folder to docker shared volume.)", default=False)
    parser.add_argument("-m", "--test", help="Run the command in test mode only, non-execution.", default=False)
    parser.add_argument("-c", "--clean", help="Remove the containers and volumes once completed.", default=True)
    parser.add_argument("-v", "--volume", help="Specify the name of the volume(s) to present to the containers.", default=None, action='append')
    parser.add_argument("-r", "--report", help="Report directory, specify as docker mount, example: /opt/appsecpipeline/", default="/opt/appsecpipeline/")
    parser.add_argument("--slack", help="Slack Web Hook", required=False)

    args, remaining_argv = parser.parse_known_args()

    profile = args.profile
    sourceDir = args.dir
    cleanUp = args.clean
    authFile = args.auth
    keyFile = args.key
    volumes = args.volume
    reportsDir = args.report
    test = args.test
    slack = args.slack

    appsec = pipeline.AppSecPipeline(profile, reportsDir, remaining_argv, volume=volumes, auth=authFile,
            key=keyFile, dir=sourceDir, test=test, clean=cleanUp, slack=slack)

    if appsec.runPipeline():
        print "**********************************************"
        print "Container UUID Prefix: " + appsec.pipelineLaunchUID
        print "Setup Docker: " + appsec.getContainerName("setup")
        """
        if volumeMount is None:
            print "Volume: " + getVolumeName(pipelineLaunchUID)
        else:
            print "Shared Volume: " + volumeMount
        """
        print "**********************************************\n\n"
        print "Complete!\n\n"
    else:
        print "Profile not found."
