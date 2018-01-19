from . import __version__ as version
import docker
import yaml
import os
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

class AppSecPipeline(object):
    """AppSecPipeline."""

    def __init__(self, profile, report, toolargs, volume=None, auth=None, key=None, dir=None, test=False, clean=True, slack=None):
        """Initialize an AppSecPipeline instance.

        :param profile: The pipeline profile to run from master.yaml
        :param report: Report directory, specify as docker mount, example: /opt/appsecpipeline/".
        :param toolargs: Tool arguments in the format URL=<url>.
        :param volume: Specify the name of the volume(s) to present to the containers.
        :param auth: Tool configuration credentials and or API keys..
        :param key: Key file for auth credentials.
        :param dir: Directory to include in docker scan. (Copies folder to docker shared volume.).
        :param test: Run the command in test mode only, non-execution.
        :param clean: Remove the containers and volumes once completed.
        :param slack: Slack web hook for alerts.
        """

        self.profile = profile
        self.report = report
        self.volume = volume
        self.auth = auth
        self.key = key
        self.dir = dir
        self.test = test
        self.clean = clean
        self.baseLocation = "../../controller"
        self.toolargs = toolargs
        self.langFile = None
        self.client = docker.from_env()
        self.lowLevelclient = docker.APIClient(base_url='unix://var/run/docker.sock')
        #docker.APIClient(base_url='unix://var/run/docker.sock')
        self.pipelineLaunchUID = str(uuid.uuid4())
        self.color = 0
        self.tcolors = ('\033[90m', '\033[93m', '\033[94m', '\033[95m', '\033[96m', '\033[33m', '\033[34m', '\033[35m', '\033[36m')
        self.ENDC = '\033[0m'
        self.slack = slack

    def runPipeline(self):
        foundProfile = False
        profile = self.profile
        volumes = self.volume
        reportsDir = self.report
        authFile = self.auth
        key = self.key

        masterYaml = self.getYamlConfig("master.yaml")
        toolYaml = self.getYamlConfig("secpipeline-config.yaml")

        #Validates that a docker network exists named appsecpipeline
        self.checkNetwork()

        #If a encrypted auth file exists the copy the file to the reports directory in the docker container
        key = None
        if self.auth:
            self.getConfigPath(volumes, reportsDir, authFile)

            #Fetch the key
            key = self.getKey(self.key)

        #Copy source or files to the docker container
        sourceContainer = None
        if self.dir is not False:
            print self.getContainerName("setup")
            print "Copying folder: %s to /var/appsecpipeline" % sourceDir
            #Start a container for copying the folder
            sourceContainer = self.launchContainer(client, "appsecpipeline/base", "setup", "/bin/bash", tty=True, volumePath=volumeMount, authFile=authFile)
            copytoContainer(self.getContainerName("setup"), sourceDir, "/opt/appsecpipeline")
            #Stop the setup container
            self.lowLevelclient.stop(container=appsec.getContainerName("setup"))

        if self.slack:
            slackTxt = "Security Pipeline Scan for: " + appsec.substituteArgs(None, self.toolargs, "", "URL", authFile=None)
            appsec.chatAlert("*Starting:* " + slackTxt)

        runeveryTool = None
        runeveryProfile = None
        finalTool = None
        finalProfile = None

        #Select the profile from the master profile file and iterate through the data
        if self.profile in masterYaml["profiles"]:
            foundProfile = True
            #Startup tool that is run ahead of all other tools in the pipeline
            if "startup" in masterYaml["profiles"][profile]:
                startupTool = masterYaml["profiles"][profile]["startup"]["tool"]
                startupProfile = masterYaml["profiles"][profile]["startup"]["profile"]
                volume = self.toolLaunch(toolYaml, startupTool, startupProfile, self.toolargs, None, None, volumes=volumes, reportsDir=reportsDir, authFile=authFile, key=key)

            #Tool that is run after every tool, for example running defectdojo to push reports after the tool has completed
            if "runevery" in masterYaml["profiles"][profile]:
                runeveryTool = masterYaml["profiles"][profile]["runevery"]["tool"]
                runeveryProfile = masterYaml["profiles"][profile]["runevery"]["profile"]

            #Final tool that is run in the pipeline
            if "final" in masterYaml["profiles"][profile]:
                finalTool = masterYaml["profiles"][profile]["final"]["tool"]
                finalProfile = masterYaml["profiles"][profile]["final"]["profile"]

            finalPipelineTool = self.pipelineTools(masterYaml["profiles"][profile]["pipeline"])

            #Iterate through the tools in the pipeline
            for tool in masterYaml["profiles"][profile]["pipeline"]:
                toolName = tool['tool']
                toolProfile = tool['tool-profile']

                volume = self.toolLaunch(toolYaml, toolName, toolProfile, self.toolargs, runeveryTool, runeveryProfile, volumes=volumes, reportsDir=reportsDir, authFile=authFile, key=key)

                #Final command on pipeline
                if toolName == finalPipelineTool and finalTool is not None:
                    volume = self.toolLaunch(toolYaml, finalTool, finalProfile, self.toolargs, None, None, volumes=volumes, reportsDir=reportsDir, authFile=authFile, key=key)

            #Clean up docker containers and volumes
            if self.clean:
                self.cleanUpDocker(sourceContainer)

            if self.slack:
                self.chatAlert("*Complete:* " + slackTxt)

        return foundProfile

    def cleanUpDocker(self, sourceContainer):

        if sourceContainer:
            print "Pausing for containers to stop..."
            sourceContainer.reload()
            print sourceContainer.status
            while sourceContainer.status != 'exited':
                sourceContainer.reload()
                print sourceContainer.status

        #Clean up Dockers
        self.client.containers.prune(filters={"label": "appsecpipeline", "label": self.pipelineLaunchUID})

        #Remove temporary shared folder
        #self.deleteVolume(volume)

    def substituteArgs(self, toolName, args, command, find=None, authFile=None):
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

    def getYamlConfig(self, yamlFile):
        yamlConfig = None
        #Expecting config file in tools/toolname/config.yaml
        yamlLoc = os.path.join(self.baseLocation, yamlFile)

        if not os.path.exists(yamlLoc):
            raise RuntimeError("Tool config does not exist. Checked in: " + yamlLoc)

        with open(yamlLoc, 'r') as stream:
            try:

                yamlConfig = yaml.safe_load(stream)

            except yaml.YAMLError as exc:
                print(exc)

        return yamlConfig

    def launcherControl(self, client, docker, tool, command, toolProfile, volumes=None):
        runContainer = False
        #Check tool profile (dynamic/static/code-analyzer)
        toolType = toolProfile["type"]

        if toolType == "dynamic":
            runContainer = True
        elif toolType == "static":
            if self.checkToolLanguage(toolProfile["languages"]):
                runContainer = True
            else:
                print "Tool %s Skipped, tool doesn't support language." % tool
                runContainer = False
        elif toolType == "code-analyzer":
            runContainer = True
        else:
            runContainer = True

        if runContainer:
            self.launchContainer(client, docker, tool, command, volumes=volumes)
        else:
            print "Skipped  %s" % (tool)

        if toolType == "code-analyzer":
            self.checkLanguages(self.getContainerName(tool))

    def launchContainer(self, client, docker, tool, command, tty=False, volumes=None):
        #Container Launch
        containerName = self.getContainerName(tool)

        print "Launch Command: %s" % command

        container = client.containers.run(docker, command, network='appsecpipeline_default',
        name=containerName, labels=["appsecpipeline",self.pipelineLaunchUID],
        detach=True, volumes=volumes, tty=tty, user=1000)
        #working_dir='/var/appsecpipeline',

        print "\033[95mContainer Info: %s %s\nContainer Name: %s with a Container ID of %s" % (docker, self.ENDC, containerName, container.id)

        #if tty don't wait for logs as it will "hang"
        if tty == False:
            for line in container.logs(stream=True):
                print self.tcolors[self.color] + tool.ljust(15) + " | \033[0m " + line.strip()
            if self.color < len(self.tcolors):
                self.color = self.color + 1
            else:
                self.color = 0
        return container

    def createVolumes(self, volumes, reportDir):
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
            volumeName = self.getVolumeName(prefixName=volumeCount)

            if os.path.exists(volumeLocalPath) == False:
                print "Source Volume Path does not exist: %s, exiting." % volumeLocalPath
                exit()

            volumeLocalPath = self.createUIDFolder(reportDir, volumeLocalPath, volumeDestPath)

            dataVolume[volumeLocalPath] = {'bind': volumeDestPath, 'mode': 'rw'}

            volume = self.client.volumes.create(name=volumeName, driver='local',
                driver_opts={'type': 'tmpfs', 'device': 'tmpfs', 'o':'uid=1000'},
                labels={"appsecpipeline": self.pipelineLaunchUID})

            volumeCount = volumeCount + 1

        return dataVolume

    def createUIDFolder(self, reportDir, volumeLocalPath, volumeDestPath):
        if reportDir == volumeDestPath:
            #Create the guid folder in the shared reports directory
            #Example: /local/directory/<guid>/
            #Mounts to: /dockerdir/reports
            volumeLocalPath = os.path.join(volumeLocalPath, self.pipelineLaunchUID)
            if os.path.exists(volumeLocalPath) == False:
                os.mkdir(volumeLocalPath)

        return volumeLocalPath

    def getVolumeName(self, prefixName=None):
        volumeName = self.pipelineLaunchUID + "_appsecpipeline"

        if prefixName is not None:
            volumeName = str(prefixName) + "_" + volumeName
        return volumeName

    def getContainerName(self, tool):
        return self.pipelineLaunchUID + "_" + tool

    def deleteVolume(self, volume):
        return volume.remove()

    def checkToolLanguage(self, toolLanguage):
        global langFile
        langFound = False
        for language in toolLanguage:
            if language.lower() in langFile:
                langFound = True
                exit

        return langFound

    def checkLanguages(self, containerName):
        #add try catch
        global langFile
        client = docker.APIClient(base_url='unix://var/run/docker.sock')

        try:
            stream, stat = client.get_archive(containerName, "/opt/appsecpipeline/reports/cloc/languages.json")
        except:
            print "Language file not found, halting pipeline."
            exit()

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

    def copytoContainer(self, containerName, source, dest):
        tarstream = io.BytesIO()

        if os.path.exists(source) == False:
            print "Source folder direction does not exist: %s, exiting." % source
            exit()

        with tarfile.open(fileobj=tarstream, mode='w') as tarfile_:
            tarfile_.add(source, arcname=os.path.basename(source))

        tarstream.seek(0)
        client = docker.APIClient(base_url='unix://var/run/docker.sock')
        client.put_archive(container=containerName, path=dest, data=tarstream)

    def checkNetwork(self):
        networkName = "appsecpipeline_default"
        client = docker.from_env()
        appNetwork = client.networks.list(networkName)

        if len(appNetwork) == 0:
            print "Creating network: %s" % networkName
            createNetwork(networkName)
        else:
            print "Network exists: %s " % networkName

    def createNetwork(self, networkName):
        client.networks.create(networkName, driver="bridge")

    def slackAlert(self, **kwargs):
        slack_web_hook = self.slack

        payload_json = json.dumps(kwargs)
        webhook_url = "https://hooks.slack.com/services/%s" % slack_web_hook

        response = requests.post(
            webhook_url, data=payload_json,
            headers={'Content-Type': 'application/json'}
        )

    def chatAlert(self, text):
        self.slackAlert(text=text, channel="#security-appsec", username="AppSecPipeline", icon_emoji=":secret:")

    def getCommand(self, toolName, profile, commands, runeveryTool, runeveryProfile, authFile=None, key=None):
        command = "-t %s -p %s %s" % (toolName, profile, commands)

        if authFile and key:
            command = "%s -a \"%s\" -k \"%s\" " % (command, authFile, key)

        if runeveryTool is not None:
            command += " --runevery %s --runevery-profile %s" % (runeveryTool, runeveryProfile)
        return command

    def toolLaunch(self, toolYaml, toolName, toolProfile, remaining_argv, runeveryTool, runeveryProfile, reportsDir=None, volumes=None, authFile=None, key=None):
        self.chatAlert(">>>*Executing:* " + toolName)

        print "***** Tool Details *****"
        toolDetails = toolYaml[toolName]
        command = "%s %s" % (toolDetails["profiles"][toolProfile], toolDetails["commands"]["exec"])
        toolArgs = self.substituteArgs(toolName, remaining_argv, command, authFile=authFile)

        if runeveryTool is not None:
            print "***** runevery Tool Details *****"
            toolruneveryDetails = toolYaml[runeveryTool]
            command = "%s %s" % (toolruneveryDetails["profiles"][runeveryProfile], toolruneveryDetails["commands"]["exec"])
            toolArgs += self.substituteArgs(toolName, remaining_argv, command, authFile==authFile)

        dockerAuthLoc = None

        if authFile and key:
            dockerAuthLoc = os.path.join(reportsDir, os.path.basename(authFile))

        dockerCommand = self.getCommand(toolName, toolProfile, toolArgs, runeveryTool, runeveryProfile, authFile=dockerAuthLoc, key=key)

        createdVolumes = self.createVolumes(volumes, reportsDir)

        self.launcherControl(self.client, toolDetails["docker"], toolName, dockerCommand, toolDetails, volumes=createdVolumes)

        return volumes

    def pipelineTools(self, pipelineTools):
        self.chatAlert("*Tools that will be run:* ")
        appSecPipeline = ""
        toolName = None
        for tool in pipelineTools:
            toolName = tool['tool']
            appSecPipeline += toolName + ", "

        self.chatAlert(">>>*AppSecPipeline:* " + appSecPipeline[:-2])

        return toolName

    def getConfigPath(self, volumes, reportsDir, configFile):
        filename = None
        for volume in volumes:
            #Volume format: localPath:/opt/dest/path
            volumeLocalPath = volume.split(":")[0]
            volumeDestPath = volume.split(":")[1]

            if reportsDir == volumeDestPath:
                sourceConfigFile = os.path.join(volumeLocalPath, "config", configFile)
                volumeDestPath = self.createUIDFolder(reportsDir, volumeLocalPath, volumeDestPath)
                volumeDestPathComplete = os.path.join(volumeDestPath, os.path.basename(configFile))

                copyfile(sourceConfigFile, volumeDestPathComplete)
                filename = volumeLocalPath
                exit

        return filename

    def getKey(self, keyFile):
        keyFile = open(keyFile,"r")
        key = keyFile.read()
        keyFile.close
        return key
