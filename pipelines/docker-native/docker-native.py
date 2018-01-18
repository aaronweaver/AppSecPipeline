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
from shutil import copyfile

baseLocation = "../../controller"
langFile = None
color = 0
tcolors = ('\033[90m', '\033[93m', '\033[94m', '\033[95m', '\033[96m', '\033[33m', '\033[34m', '\033[35m', '\033[36m')
ENDC = '\033[0m'

def substituteArgs(toolName, args, command, find=None, authFile=None):
    toolArguments = ""
    authFileYaml = None

    if authFile:
        #AuthFile is relative to the report file directory
        with open(authFile, 'r') as stream:
            try:
                #Tool configuration
                authFileYaml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                logging.warning(exc)

    for arg in args:
        if "=" in arg:
            env = arg.split("=", 1)
            if env[0] == find:
                toolArguments = env[1]
            #Subsitute the user-defined parameters
            if env[0] in command:
                toolArguments = "%s %s " % (arg, toolArguments)

    if authFile:
        if toolName in authFileYaml:
            toolParameters = authFileYaml[toolName]["parameters"]

            for parameter in toolParameters:
                toolSecret = "%s=%s" % (parameter, toolParameters[parameter]["value"])
                toolArguments = "%s %s " % (toolSecret, toolArguments)

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

def launcherControl(client, docker, tool, command, pipelineLaunchUID, toolProfile, volumes=None):
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
        launchContainer(client, docker, tool, command, pipelineLaunchUID, volumes=volumes)
    else:
        print "Skipped  %s" % (tool)

    if toolType == "code-analyzer":
        checkLanguages(getContainerName(pipelineLaunchUID, tool))

def launchContainer(client, docker, tool, command, pipelineLaunchUID, tty=False, volumes=None):
    global color

    #Container Launch
    containerName = getContainerName(pipelineLaunchUID, tool)

    print "Launch Command: %s" % command

    container = client.containers.run(docker, command, network='appsecpipeline_default',
    name=containerName, labels=["appsecpipeline",pipelineLaunchUID],
    detach=True, volumes=volumes, tty=tty, user=1000)
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

def createVolumes(volumes, pipelineLaunchUID, reportDir):
    volumeCount = 1
    dataVolume = {}

    for volume in volumes:
        #Volume format: localPath:/opt/dest/path
        volumeLocalPath = volume.split(":")[0]
        volumeDestPath = volume.split(":")[1]

        if os.path.exists(volumeLocalPath) == False:
            print "Source Volume Path does not exist: %s, exiting." % volumePath
            exit()

        #Shared volume name
        volumeName = getVolumeName(pipelineLaunchUID, prefixName=volumeCount)

        if os.path.exists(volumeLocalPath) == False:
            print "Source Volume Path does not exist: %s, exiting." % volumeLocalPath
            exit()

        volumeLocalPath = createUIDFolder(reportDir, volumeLocalPath, volumeDestPath)

        dataVolume[volumeLocalPath] = {'bind': volumeDestPath, 'mode': 'rw'}

        volume = client.volumes.create(name=volumeName, driver='local',
            driver_opts={'type': 'tmpfs', 'device': 'tmpfs', 'o':'uid=1000'},
            labels={"appsecpipeline": pipelineLaunchUID})

        volumeCount = volumeCount + 1

    return dataVolume

def createUIDFolder(reportDir, volumeLocalPath, volumeDestPath):
    if reportDir == volumeDestPath:
        #Create the guid folder in the shared reports directory
        #Example: /local/directory/<guid>/
        #Mounts to: /dockerdir/reports
        volumeLocalPath = os.path.join(volumeLocalPath,pipelineLaunchUID)

        if os.path.exists(volumeLocalPath) == False:
            os.mkdir(volumeLocalPath)

    return volumeLocalPath

def getVolumeName(pipelineLaunchUID, prefixName=None):
    volumeName = pipelineLaunchUID + "_appsecpipeline"

    if prefixName is not None:
        volumeName = str(prefixName) + "_" + volumeName
    return volumeName

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
    stream, stat = client.get_archive(containerName, "/opt/appsecpipeline/reports/cloc/languages.json")

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

def getCommand(toolName, profile, commands, runeveryTool, runeveryProfile, authFile=None, key=None):
    command = "-t %s -p %s %s" % (toolName, profile, commands)

    if authFile and key:
        command = "%s -a \"%s\" -k \"%s\" " % (command, authFile, key)

    if runeveryTool is not None:
        command += " --runevery %s --runevery-profile %s" % (runeveryTool, runeveryProfile)
    return command

def toolLaunch(toolName, toolProfile, runeveryTool, runeveryProfile, reportsDir=None, volumes=None, authFile=None, key=None):
    chatAlert(">>>*Executing:* " + toolName + ": " + slackTxt)

    print "***** Tool Details *****"
    toolDetails = toolYaml[toolName]
    command = "%s %s" % (toolDetails["profiles"][toolProfile], toolDetails["commands"]["exec"])
    toolArgs = substituteArgs(toolName, remaining_argv, command, authFile=authFile)

    if runeveryTool is not None:
        print "***** runevery Tool Details *****"
        toolruneveryDetails = toolYaml[runeveryTool]
        command = "%s %s" % (toolruneveryDetails["profiles"][runeveryProfile], toolruneveryDetails["commands"]["exec"])
        toolArgs += substituteArgs(toolName, remaining_argv, command, authFile==authFile)

    dockerAuthLoc = None
    if authFile and key:
        dockerAuthLoc = os.path.join(reportsDir, os.path.basename(authFile))
        
    dockerCommand = getCommand(toolName, toolProfile, toolArgs, runeveryTool, runeveryProfile, authFile=dockerAuthLoc, key=key)

    createdVolumes = createVolumes(volumes, pipelineLaunchUID, reportsDir)

    launcherControl(client, toolDetails["docker"], toolName, dockerCommand, pipelineLaunchUID, toolDetails, volumes=createdVolumes)

    return volumes

def pipelineTools(pipelineTools):
    chatAlert("*Tools that will be run:* ")
    appSecPipeline = ""
    toolName = None
    for tool in pipelineTools:
        toolName = tool['tool']
        appSecPipeline += toolName + ", "

    chatAlert(">>>*AppSecPipeline:* " + appSecPipeline[:-2])

    return toolName

def getConfigPath(volumes, reportsDir, configFile, pipelineLaunchUID):
    filename = None
    for volume in volumes:
        #Volume format: localPath:/opt/dest/path
        volumeLocalPath = volume.split(":")[0]
        volumeDestPath = volume.split(":")[1]

        if reportsDir == volumeDestPath:
            sourceConfigFile = os.path.join(volumeLocalPath, "config", configFile)
            volumeDestPath = createUIDFolder(reportsDir, volumeLocalPath, volumeDestPath)
            volumeDestPath = os.path.join(volumeDestPath, configFile)
            copyfile(sourceConfigFile, volumeDestPath)
            filename = volumeLocalPath
            exit

    return filename

def getKey(keyFile):
    keyFile = open(keyFile,"r")
    key = keyFile.read()
    keyFile.close
    return key
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

    args, remaining_argv = parser.parse_known_args()
    profile = args.profile
    sourceDir = args.dir
    cleanUp = args.clean
    sourceContainer = None
    authFile = args.auth
    keyFile = args.key
    volumes = args.volume
    reportsDir = args.report

    masterYaml = getYamlConfig("master.yaml")
    toolYaml = getYamlConfig("secpipeline-config.yaml")

    #Setup docker connection
    client = docker.from_env()
    lowLevelclient = docker.APIClient(base_url='unix://var/run/docker.sock')

    #Check shared network
    checkNetwork()

    #Unique ID for each "build"
    pipelineLaunchUID = str(uuid.uuid4())

    #Copy Auth file to shared directory
    key = None
    if authFile and key:
        getConfigPath(volumes, reportsDir, authFile, pipelineLaunchUID)

        #Fetch the key
        key = getKey(keyFile)

    if sourceDir is not False:
        print getContainerName(pipelineLaunchUID, "setup")
        print "Copying folder: %s to /var/appsecpipeline" % sourceDir
        #Start a container for copying the folder
        sourceContainer = launchContainer(client, "appsecpipeline/base", "setup", "/bin/bash", pipelineLaunchUID, tty=True, volumePath=volumeMount, authFile=authFile)
        copytoContainer(getContainerName(pipelineLaunchUID, "setup"), sourceDir, "/var/appsecpipeline")
        #Stop the setup container
        lowLevelclient.stop(container=getContainerName(pipelineLaunchUID, "setup"))

    slackTxt = "Security Pipeline Scan for: " + substituteArgs(None, remaining_argv, "", "URL", authFile=None)
    chatAlert("*Starting:* " + slackTxt)

    runeveryTool = None
    runeveryProfile = None
    finalTool = None
    finalProfile = None

    if profile in masterYaml["profiles"]:
        if "startup" in masterYaml["profiles"][profile]:
            startupTool = masterYaml["profiles"][profile]["startup"]["tool"]
            startupProfile = masterYaml["profiles"][profile]["startup"]["profile"]
            volume = toolLaunch(startupTool, startupProfile, None, None, volumes=volumes, reportsDir=reportsDir, authFile=authFile, key=key)

        if "runevery" in masterYaml["profiles"][profile]:
            runeveryTool = masterYaml["profiles"][profile]["runevery"]["tool"]
            runeveryProfile = masterYaml["profiles"][profile]["runevery"]["profile"]

        if "final" in masterYaml["profiles"][profile]:
            finalTool = masterYaml["profiles"][profile]["final"]["tool"]
            finalProfile = masterYaml["profiles"][profile]["final"]["profile"]

        finalPipelineTool = pipelineTools(masterYaml["profiles"][profile]["pipeline"])

        for tool in masterYaml["profiles"][profile]["pipeline"]:
            toolName = tool['tool']
            toolProfile = tool['tool-profile']

            volume = toolLaunch(toolName, toolProfile, runeveryTool, runeveryProfile, volumes=volumes, reportsDir=reportsDir, authFile=authFile, key=key)

            #Final command on pipeline
            if toolName == finalPipelineTool and finalTool is not None:
                volume = toolLaunch(finalTool, finalProfile, None, None, volumes=volumes, reportsDir=reportsDir, authFile=authFile, key=key)

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
            #deleteVolume(volume)

        print "**********************************************"
        print "Container UUID Prefix: " + pipelineLaunchUID
        print "Setup Docker: " + getContainerName(pipelineLaunchUID, "setup")
        """
        if volumeMount is None:
            print "Volume: " + getVolumeName(pipelineLaunchUID)
        else:
            print "Shared Volume: " + volumeMount
        """
        print "**********************************************\n\n"
        print "Complete!\n\n"
        chatAlert("*Complete:* " + slackTxt)
    else:
        print "Profile not found."
