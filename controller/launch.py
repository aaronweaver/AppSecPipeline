#!/usr/bin/env python

"""Launch.py: Starts tooling based on the supplied yaml file in support of the AppSec Pipeline."""

__author__      = "Aaron Weaver"
__copyright__   = "Copyright 2017, Aaron Weaver"

import yaml
import argparse
import sys
import shlex
import os
import string
import uuid
from subprocess import call
from datetime import datetime
import base64

baseLocation = "/usr/bin/"
reportsDir = "reports/"

#Allow for dynamic arguments to support a wide variety of tools
#Format URL=Value, YAML Definition for substitution $URL
def substituteArgs(args, command):
    for arg in args:
        #print arg
        env = arg.split("=", 1) #Only split on the first '='
        if len(env) > 1:
            name = env[0]
            value = env[1]
            #Replace values if those values exist in the command
            """
            print "name"
            print name.lower()
            print "value"
            print value
            print "Command"
            print command.lower()
            """
            if name.lower() in command.lower():
                if name.startswith('--'):
                    name = name.replace("--","", 1)

                if name.startswith('-'):
                    name = name.replace("-","", 1)

                command = command.replace("$" + name, value)
                #print "Command replaced: " + command
    return command

def slugify(s):
    """
    Normalizes string for foldername
    """
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in s if c in valid_chars)
    filename = filename.replace(' ','_') # I don't like spaces in filenames.
    return filename

def reportName(toolName, reportString):
    filename = None
    basePath = os.path.join(os.getcwd(),reportsDir,toolName)
    #basePath = os.path.join(reportsDir,toolName)

    if "{timestamp}" in reportString:
        #Add the folder path and datetimestamps
        #toolName/toolName_2017-11-02-1-05-04.csv
        datestring = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
        filename = reportString.replace("{timestamp}", os.path.join(basePath, toolName + "_" + datestring + "_" + str(uuid.uuid4())))
    else:
        #If the filename is a static name
        filename = os.path.join(basePath,reportString)

    return filename

def checkFolderPath(toolName):
    #Create a directory to store the reports / junit
    folderName = slugify(toolName)
    if not os.path.exists(reportsDir):
        os.mkdir(reportsDir)

    if not os.path.exists(reportsDir + folderName):
        os.mkdir(reportsDir + folderName)

    if not os.path.exists(reportsDir + folderName + "/junit"):
        os.mkdir(reportsDir + folderName + "/junit")

def getYamlConfig(toolName):
    #Expecting config file in tools/toolname/config.yaml
    yamlLoc = os.path.join(baseLocation, "tools",toolName,"config.yaml")

    if not os.path.exists(yamlLoc):
        raise RuntimeError("Tool config does not exist. Checked in: " + yamlLoc)

    return yamlLoc

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
    # Turn off help, so we print all options in response to -h
        add_help=False
        )
    #Command line options
    parser.add_argument("-t", "--tool", help="Tool to Run", required=True)
    parser.add_argument("-s", "--scan_type", help="Scan Type (dynamic, static)", default=None)
    parser.add_argument("-p", "--profile", help="Profile to Execute", default=None)
    parser.add_argument("-c", "--credential", help="Scan with login credentials. Specify credentialed profile.", default=None)
    parser.add_argument("-m", "--test", help="Run the command in test mode only, non-execution.", default=False)

    args, remaining_argv = parser.parse_known_args()

    yamlConfig = getYamlConfig(args.tool)

    with open(yamlConfig, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
            launchCmd = None
            report = None
            scan_type = None
            profile_run = None
            profile_found = False
            test_mode = False
            fullReportName = None
            credentialedScan = None

            if args.scan_type:
                scan_type = args.scan_type

            if args.profile:
                profile_run = args.profile

            if args.credential:
                credentialedScan = args.credential

            if args.test:
                test_mode = args.test

            #Set the object to the tool yaml section
            tool = config["tool"]
            #Tooling commands
            commands = tool["commands"]

            #if tool["type"] == scan_type:
                #Check to see if a profile exists
            for profile in tool["profiles"]:
                if profile_run in profile:
                    launchCmd = profile[profile_run]
                    profile_found = True
                #Profile not found check the attack_type
                if "attack_types" in profile and launchCmd is None:
                    for attack_type in profile["attack_types"]:
                        if attack_type == profile_run:
                            if isinstance(profile["attack_types"][profile_run], basestring):
                                launchCmd = profile["attack_types"][profile_run]
                                profile_found = True

            #Launch only if command exists
            if profile_found and launchCmd:
                if commands["report"] is not None:
                    fullReportName = reportName(slugify(tool["name"]), commands["reportname"])
                    launchCmd = launchCmd + " " + commands["report"].replace("{reportname}", fullReportName)

                #Only launch command if a launch command is specified
                #Pre and post require a launch command
                if launchCmd:
                    #Execute a pre-commmand, such as a setup or update requirement
                    if commands["pre"] is not None:
                        if not test_mode:
                            call(shlex.split(commands["pre"]))

                    #Create a directory to store the reports
                    checkFolderPath(tool["name"])
                    launchCmd = commands["exec"] + " " + launchCmd

                    #Check for credentialed scan
                    if credentialedScan is not None:
                        if "credentials" in tool:
                            if credentialedScan in tool["credentials"]:
                                launchCmd = launchCmd + " " + tool["credentials"][credentialedScan]
                            else:
                                print "Credential profile not found."
                        else:
                            print "Credential command line option passed but no credential profile exists in config.yaml."

                    print launchCmd
                    #Substitute any environment variables
                    launchCmd = substituteArgs(remaining_argv, launchCmd)
                    print "*****************************"
                    print "Launch: " + launchCmd
                    #print "Launch: " + base64.b64encode(launchCmd)
                    print "*****************************"
                    #Check for any commands that have not been substituted and warn
                    if "$" in launchCmd:
                        print "*****************************"
                        print "Warning: Some commands haven't been substituted. Please review:"
                        print launchCmd
                        print "*****************************"

                    if not test_mode:
                        if "shell" in commands:
                            if commands["shell"] == True:
                                print "Using shell call"
                                call(launchCmd, shell=True)
                            else:
                                call(shlex.split(launchCmd))
                        else:
                            call(shlex.split(launchCmd))

                    #Execute a pre-commmand, such as a setup or update requirement
                    if commands["post"] is not None:
                        #Look into making this more flexible with dynamic substitution
                        postCmd = commands["post"]
                        postCmd = postCmd.replace("{reportname}", fullReportName)
                        print "*****************************"
                        print "Post Command: " + postCmd
                        print "*****************************"
                        if not test_mode:
                            #review and see what other options we have
                            call(postCmd, shell=True)
                            #call(shlex.split(postCmd))
                            if commands["junit"] is not None:
                                #Look into making this more flexible with dynamic substitution
                                junitCmd = commands["junit"]
                                junitCmd = junitCmd.replace("{reportname}", fullReportName)
                                print "*****************************"
                                print "Junit Command: " + junitCmd
                                print "*****************************"
                                if not test_mode:
                                    #review and see what other options we have
                                    call(shlex.split(junitCmd))
            else:
                print "Profile or command to run not found in Yaml configuration file."
        #else:
        #    print "No profile or scan type found."

        except yaml.YAMLError as exc:
            print(exc)
