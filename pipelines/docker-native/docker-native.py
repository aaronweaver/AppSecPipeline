import docker
import yaml
import os
import argparse
import uuid
import tarfile
from cStringIO import StringIO
import io
import time
import shutil
import json
import requests
import sys

baseLocation = "../../controller"
langFile = None
color = 0
tcolors = ('\033[90m', '\033[93m', '\033[94m', '\033[95m', '\033[96m', '\033[33m', '\033[34m', '\033[35m', '\033[36m')
ENDC = '\033[0m'

def substituteArgs(args, command, find=None):

    toolArguments = ""

    for arg in args:
        if "=" in arg:
            env = arg.split("=", 1)
            if env[0] == find:
                toolArguments = env[1]

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

def launcherControl(client, docker, tool, command, pipelineLaunchUID, toolProfile, volumePath=None):
    runContainer = False
    #Check tool profile (dynamic/static/code-analyzer)
    toolType = toolProfile["type"]
    if toolType == "dynamic":
        runContainer = True
    elif toolType == "static":
        if checkToolLanguage(toolProfile["languages"]):
            runContainer = True
        else:
            print "Tool %s Skipped, tool doesn't support language." % tool
            runContainer = False
    elif toolType == "code-analyzer":
        runContainer = True
    else:
        runContainer = True

    if runContainer:
        launchContainer(client, docker, tool, command, pipelineLaunchUID, volumePath=volumePath)
    else:
        print "Skipped  %s" % (tool)

    if toolType == "code-analyzer":
        checkLanguages(getContainerName(pipelineLaunchUID, tool))

def launchContainer(client, docker, tool, command, pipelineLaunchUID, tty=False, volumePath=None):
    global color
    #Shared volume for reporting
    volumeToUse = getVolumeName(pipelineLaunchUID)

    if volumePath is not None:
        volumeToUse = volumePath
        #Ensure volumePath exists locally
        if os.path.exists(volumePath) == False:
            print "Source Volume Path does not exist: %s, exiting." % volumePath
            exit()
        else:
            volumeToUse = os.path.join(volumeToUse,pipelineLaunchUID)
            if os.path.exists(volumeToUse) == False:
                os.mkdir(volumeToUse)

    appsecpipelineVolume = {volumeToUse: {'bind': '/var/appsecpipeline', 'mode': 'rw'}}

    #Container Launch
    containerName = getContainerName(pipelineLaunchUID, tool)

    print "Launch Command: %s" % command

    container = client.containers.run(docker, command, network='appsecpipeline_default',
    name=containerName, labels=["appsecpipeline",pipelineLaunchUID],
    detach=True, volumes=appsecpipelineVolume, tty=tty, user=1000)
    #working_dir='/var/appsecpipeline',
    
    print "\033[95mContainer Info: %s %s\nContainer Name: %s with a Container ID of %s" % (docker, ENDC, containerName, container.id)

    #if tty don't wait for logs as it will "hang"
    if tty == False:
        for line in container.logs(stream=True):
            print tcolors[color] + tool.ljust(15) + " | \033[0m " + line.strip()
        if color < len(tcolors):
            color = color + 1
        else:
            color = 0
    return container

def createVolume(pipelineLaunchUID):
    volumeName = getVolumeName(pipelineLaunchUID)
    volume = client.volumes.create(name=volumeName, driver='local',
        driver_opts={'type': 'tmpfs', 'device': 'tmpfs', 'o':'uid=1000'},
        labels={"appsecpipeline": pipelineLaunchUID})

    return volume

def getVolumeName(pipelineLaunchUID):
    return pipelineLaunchUID + "_appsecpipeline"

def getContainerName(pipelineLaunchUID, tool):
    return pipelineLaunchUID + "_" + tool

def deleteVolume(volume):
    return volume.remove()

def checkToolLanguage(toolLanguage):
    global langFile
    langFound = False
    for language in toolLanguage:
        if language.lower() in langFile:
            langFound = True
            exit

    return langFound

def checkLanguages(containerName):
    #add try catch
    global langFile
    client = docker.APIClient(base_url='unix://var/run/docker.sock')
    stream, stat = client.get_archive(containerName, "/var/appsecpipeline/reports/cloc/languages.json")

    runId = str(uuid.uuid4())
    tarLangFile = "/tmp/" + runId + ".tar.gz"
    with open(tarLangFile, "w") as f:
        f.write(stream.read())

    f.close()
    targetDirectory = os.path.join("/tmp/",runId)
    tar = tarfile.open(tarLangFile)
    tar.extractall(targetDirectory)
    tar.close()

    with open(os.path.join(targetDirectory,"languages.json"), 'r') as f:
        langFile = f.read().lower()

    os.remove(tarLangFile)
    shutil.rmtree(targetDirectory)

def copytoContainer(containerName, source, dest):
    tarstream = io.BytesIO()

    if os.path.exists(source) == False:
        print "Source folder direction does not exist: %s, exiting." % source
        exit()

    with tarfile.open(fileobj=tarstream, mode='w') as tarfile_:
        tarfile_.add(source, arcname=os.path.basename(source))

    tarstream.seek(0)
    client = docker.APIClient(base_url='unix://var/run/docker.sock')
    client.put_archive(container=containerName, path=dest, data=tarstream)

def checkNetwork():
    networkName = "appsecpipeline_default"
    appNetwork = client.networks.list(networkName)
    appNetwork
    if len(appNetwork) == 0:
        print "Creating network: %s" % networkName
        createNetwork(networkName)
    else:
        print "Network exists: %s " % networkName

def createNetwork(networkName):
    client.networks.create(networkName, driver="bridge")

def slackAlert(**kwargs):
    slack_web_hook = os.environ["SLACK_WEB_HOOK"]

    payload_json = json.dumps(kwargs)
    webhook_url = "https://hooks.slack.com/services/%s" % slack_web_hook

    response = requests.post(
        webhook_url, data=payload_json,
        headers={'Content-Type': 'application/json'}
    )

def chatAlert(text):
    slackAlert(text=text, channel="#security-appsec", username="AppSecPipeline", icon_emoji=":secret:")

def getCommand(toolName, profile, commands, runeveryTool, runeveryProfile):
    command = "-t %s -p %s %s" % (toolName, profile, commands)

    if runeveryTool is not None:
        command += " --runevery %s --runevery-profile %s" % (runeveryTool, runeveryProfile)
    return command

def toolLaunch(toolName, toolProfile, runeveryTool, runeveryProfile):
    chatAlert(">>>*Executing:* " + toolName + ": " + slackTxt)

    print "***** Tool Details *****"
    toolDetails = toolYaml[toolName]
    command = "%s %s" % (toolDetails["profiles"][toolProfile], toolDetails["commands"]["exec"])
    toolArgs = substituteArgs(remaining_argv, command)

    if runeveryTool is not None:
        print "***** runevery Tool Details *****"
        toolruneveryDetails = toolYaml[runeveryTool]
        command = "%s %s" % (toolruneveryDetails["profiles"][runeveryProfile], toolruneveryDetails["commands"]["exec"])
        toolArgs += substituteArgs(remaining_argv, command)

    dockerCommand = getCommand(toolName, toolProfile, toolArgs, runeveryTool, runeveryProfile)

    volume = createVolume(pipelineLaunchUID)
    launcherControl(client, toolDetails["docker"], toolName, dockerCommand, pipelineLaunchUID, toolDetails, volumePath=volumeMount)
    return volume

def pipelineTools(pipelineTools):
    chatAlert("*Tools that will be run:* ")
    appSecPipeline = ""
    toolName = None
    for tool in pipelineTools:
        toolName = tool['tool']
        appSecPipeline += toolName + ", "

    chatAlert(">>>*AppSecPipeline:* " + appSecPipeline[:-2])

    return toolName

if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    #Command line options
    parser.add_argument("-p", "--profile", help="Run the command in test mode only, non-execution.", required=True)
    parser.add_argument("-d", "--dir", help="Directory to include in docker scan. (Copies folder to docker shared volume.)", default=False)
    parser.add_argument("-m", "--test", help="Run the command in test mode only, non-execution.", default=False)
    parser.add_argument("-c", "--clean", help="Remove the containers and volumes once completed.", default=True)
    parser.add_argument("-v", "--volume", help="Specify the name of the volume to present to the containers.", default=None)

    args, remaining_argv = parser.parse_known_args()
    profile = args.profile
    sourceDir = args.dir
    cleanUp = args.clean
    volumeMount = args.volume
    sourceContainer = None

    masterYaml = getYamlConfig("master.yaml")
    toolYaml = getYamlConfig("secpipeline-config.yaml")

    #Setup docker connection
    client = docker.from_env()
    lowLevelclient = docker.APIClient(base_url='unix://var/run/docker.sock')

    #Check shared network
    checkNetwork()

    #Unique ID for each "build"
    pipelineLaunchUID = str(uuid.uuid4())

    if sourceDir is not False:
        print getContainerName(pipelineLaunchUID, "setup")
        print "Copying folder: %s to /var/appsecpipeline" % sourceDir
        #Start a container for copying the folder
        sourceContainer = launchContainer(client, "appsecpipeline/base", "setup", "/bin/bash", pipelineLaunchUID, tty=True, volumePath=volumeMount)
        copytoContainer(getContainerName(pipelineLaunchUID, "setup"), sourceDir, "/var/appsecpipeline")
        #Stop the setup container
        lowLevelclient.stop(container=getContainerName(pipelineLaunchUID, "setup"))

    slackTxt = "Security Pipeline Scan for: " + substituteArgs(remaining_argv, "", "URL")
    chatAlert("*Starting:* " + slackTxt)

    runeveryTool = None
    runeveryProfile = None
    finalTool = None
    finalProfile = None

    if profile in masterYaml["profiles"]:
        if "startup" in masterYaml["profiles"][profile]:
            startupTool = masterYaml["profiles"][profile]["startup"]["tool"]
            startupProfile = masterYaml["profiles"][profile]["startup"]["profile"]
            volume = toolLaunch(startupTool, startupProfile, None, None)

        if "runevery" in masterYaml["profiles"][profile]:
            runeveryTool = masterYaml["profiles"][profile]["runevery"]["tool"]
            runeveryProfile = masterYaml["profiles"][profile]["runevery"]["profile"]

        if "final" in masterYaml["profiles"][profile]:
            finalTool = masterYaml["profiles"][profile]["final"]["tool"]
            finalProfile = masterYaml["profiles"][profile]["final"]["profile"]

        finalPipelineTool = pipelineTools(masterYaml["profiles"][profile]["pipeline"])

        for tool in masterYaml["profiles"][profile]["pipeline"]:
            toolName = tool['tool']
            toolProfile = tool['profile']

            volume = toolLaunch(toolName, toolProfile, runeveryTool, runeveryProfile)

            #Final command on pipeline
            if toolName == finalPipelineTool and finalTool is not None:
                volume = toolLaunch(finalTool, finalProfile, None, None)

        if cleanUp == True:
            #Clean up time
            if sourceContainer:
                print "Pausing for containers to stop..."
                sourceContainer.reload()
                print sourceContainer.status
                while sourceContainer.status != 'exited':
                    sourceContainer.reload()
                    print sourceContainer.status

            #Clean up Dockers
            client.containers.prune(filters={"label": "appsecpipeline", "label": pipelineLaunchUID})

            #Remove temporary shared folder
            deleteVolume(volume)

        print "**********************************************"
        print "Container UUID Prefix: " + pipelineLaunchUID
        print "Setup Docker: " + getContainerName(pipelineLaunchUID, "setup")
        if volumeMount is None:
            print "Volume: " + getVolumeName(pipelineLaunchUID)
        else:
            print "Shared Volume: " + volumeMount
        print "**********************************************\n\n"
        print "Complete!\n\n"
        chatAlert("*Complete:* " + slackTxt)
    else:
        print "Profile not found."
