import docker
import yaml
import os
import argparse
import uuid
import tarfile
from cStringIO import StringIO
import io
import time

baseLocation = "../../controller"

def substituteArgs(args, command):

    toolArguments = ""

    for arg in args:
        if "=" in arg:
            env = arg.split("=", 1)
            if env[0] in command:
                toolArguments = "%s %s " % (arg, toolArguments)
    return toolArguments

def getYamlConfig(yamlFile):
    yamlConfig = None
    #Expecting config file in tools/toolname/config.yaml
    yamlLoc = os.path.join(baseLocation, yamlFile)

    if not os.path.exists(yamlLoc):
        raise RuntimeError("Tool config does not exist. Checked in: " + yamlLoc)

    with open(yamlLoc, 'r') as stream:
        try:

            yamlConfig = yaml.safe_load(stream)

        except yaml.YAMLError as exc:
            print(exc)

    return yamlConfig

def getCommand(toolName, profile, commands):
    command = "launch.py -t %s -p %s %s" % (toolName, profile, commands)

    return command

def launcherControl(client, docker, tool, command, pipelineLaunchUID, toolProfile):
    runContainer = False
    #Check tool profile (dynamic/static/code-analyzer)
    toolType = toolProfile["type"]
    if toolType == "dynamic":
        runContainer = True
    elif toolType == "static":
        runContainer = True
    elif toolType == "code-analyzer":
        runContainer = True

    if runContainer:
        launchContainer(client, docker, tool, command, pipelineLaunchUID)
    else:
        print "Skipped Tool: %s" % (tool)

    if toolType == "code-analyzer":
        checkLanguages(getContainerName(pipelineLaunchUID, tool))

def launchContainer(client, docker, tool, command, pipelineLaunchUID, tty=False):
    #Shared volume for reporting
    appsecpipelineVolume = {getVolumeName(pipelineLaunchUID): {'bind': '/var/appsecpipeline', 'mode': 'rw'}}

    #Container Launch
    containerName = getContainerName(pipelineLaunchUID, tool)
    container = client.containers.run(docker, command, network='appsecpipeline_default', working_dir='/var/appsecpipeline', name=containerName, labels=["appsecpipeline",pipelineLaunchUID], detach=True, volumes=appsecpipelineVolume, tty=tty)

    print "Launching Image: %s Container Name: %s with a Container ID of %s" % (docker, containerName, container.id)
    #if tty don't wait for logs as it will "hang"
    if tty == False:
        for line in container.logs(stream=True):
            print tool.ljust(15) + " | " + line.strip()

def createVolume(pipelineLaunchUID):
    volumeName = getVolumeName(pipelineLaunchUID)
    volume = client.volumes.create(name=volumeName, driver='local',
        labels={"appsecpipeline": pipelineLaunchUID})

    return volume

def getVolumeName(pipelineLaunchUID):
    return pipelineLaunchUID + "_appsecpipeline"

def getContainerName(pipelineLaunchUID, tool):
    return pipelineLaunchUID + "_" + tool

def deleteVolume(volume):
    return volume.remove()

def checkLanguages(containerName):
    print "Not implemented"
    #client = docker.APIClient(base_url='unix://var/run/docker.sock')
    #print client.copy(container=containerName, resource="/var/appsecpipeline/reports/cloc/languages.json")
    #stream, stat = client.get_archive("appsecpipeline_jenkins-pipeline_1", "/etc/passwd")
    #raw_data=stream.read()
    #tar = tarfile.open(mode= "r|", fileobj = StringIO(stream))

def copytoContainer(containerName, source, dest):
    tarstream = io.BytesIO()
    with tarfile.open(fileobj=tarstream, mode='w') as tarfile_:
        tarfile_.add(source, arcname=os.path.basename(source))

    tarstream.seek(0)
    client = docker.APIClient(base_url='unix://var/run/docker.sock')
    client.put_archive(container=containerName, path=dest, data=tarstream)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    #Command line options
    parser.add_argument("-p", "--profile", help="Run the command in test mode only, non-execution.", required=True)
    parser.add_argument("-d", "--dir", help="Directory to include in docker scan. (Copies folder to docker shared volume.)", default=False)
    parser.add_argument("-m", "--test", help="Run the command in test mode only, non-execution.", default=False)
    parser.add_argument("-c", "--clean", help="Remove the containers and volumes once completed.", default=True)

    args, remaining_argv = parser.parse_known_args()
    profile = args.profile
    sourceDir = args.dir
    cleanUp = args.clean

    masterYaml = getYamlConfig("master.yaml")
    toolYaml = getYamlConfig("secpipeline-config.yaml")

    client = docker.from_env()

    #Unique ID for each "build"
    pipelineLaunchUID = str(uuid.uuid4())

    if sourceDir is not False:
        print getContainerName(pipelineLaunchUID, "setup")
        print "Copying folder: %s to /var/appsecpipeline" % sourceDir
        #Start a container for copying the folder
        launchContainer(client, "appsecpipeline/base", "setup", "/bin/bash", pipelineLaunchUID, tty=True)
        copytoContainer(getContainerName(pipelineLaunchUID, "setup"), sourceDir, "/var/appsecpipeline")
        #Stop the setup container
        lowLevelclient = docker.APIClient(base_url='unix://var/run/docker.sock')
        lowLevelclient.stop(container=getContainerName(pipelineLaunchUID, "setup"))

    for tool in masterYaml["profiles"][profile]:
        toolName = tool['tool']
        toolProfile = tool['profile']

        print "***** Tool Details *****"
        toolDetails = toolYaml[toolName]
        command = "%s %s" % (toolDetails["profiles"][toolProfile], toolDetails["commands"]["exec"])
        toolArgs = substituteArgs(remaining_argv, command)
        dockerCommand = getCommand(toolName, toolProfile, toolArgs)

        volume = createVolume(pipelineLaunchUID)
        launcherControl(client, toolDetails["docker"], toolName, dockerCommand, pipelineLaunchUID, toolDetails)

    if cleanUp:
        #Clean up time
        print "Pausing for containers to stop..."
        time.sleep(8)

        #Clean up Dockers
        client.containers.prune(filters={"label": "appsecpipeline", "label": pipelineLaunchUID})

        #Remove temporary shared folder
        deleteVolume(volume)

    print "**********************************************"
    print "Container UUID Prefix: " + pipelineLaunchUID
    print "Setup Docker: " + getContainerName(pipelineLaunchUID, "setup")
    print "Shared Volume: " + getVolumeName(pipelineLaunchUID)
    print "**********************************************\n\n"
    print "Complete!\n\n"
