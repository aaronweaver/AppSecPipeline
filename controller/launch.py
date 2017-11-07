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

baseLocation = "/usr/bin/"
reportsDir = "reports/"

def substituteArgs(args, command):
    for arg in args:
        env = arg.split("=")
        if len(env) > 1:
            name = env[0]
            value = env[1]
            #Replace values if those values exist in the command
            if name in command:
                command = command.replace("$" + name, value)
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
    datestring = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')

    #Add the folder path and datetimestamps
    #toolName/toolName_2017-11-02-1-05-04.csv
    filename = tool["report"].replace("{timestamp}", reportsDir + toolName + "/" + toolName + "_" + datestring + "_" + str(uuid.uuid4()))

    return filename

def checkFolderPath(toolName):
    #Create a directory to store the reports
    folderName = slugify(toolName)
    if not os.path.exists(reportsDir):
        os.mkdir(reportsDir)

    if not os.path.exists(reportsDir + folderName):
        os.mkdir(reportsDir + folderName)

def getYamlConfig(toolName):
    #Expecting config file in tools/toolname/config.yaml
    yamlLoc = baseLocation + "tools/" + toolName + "/config.yaml"
    if not os.path.exists(yamlLoc):
        raise RuntimeError("Tool config does not exist")

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
    parser.add_argument("-m", "--test", help="Run the command in test mode only, non-execution.", default=False)

    args, remaining_argv = parser.parse_known_args()

    yamlConfig = getYamlConfig(args.tool)

    with open(yamlConfig, 'r') as stream:
        try:
            config = yaml.load(stream)
            launchCmd = None
            report = None
            scan_type = None
            profile_run = None
            profile_found = False
            test_mode = False

            if args.scan_type:
                scan_type = args.scan_type

            if args.profile:
                profile_run = args.profile

            if args.test:
                test_mode = args.test

            #Set the object to the tool yaml section
            tool = config["tool"]

            #Only run the tool if setting is for that kind of security tool: example: dynamic/static
            if tool["type"] == scan_type:
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
                    #Execute a pre-commmand, such as a setup or update requirement
                    if tool["pre"] is not None:
                        if not test_mode:
                            call(shlex.split(tool["pre"]))

                    if tool["report"] is not None:
                        launchCmd = launchCmd + " " + reportName(slugify(tool["name"]), tool["report"])

                    if launchCmd:
                        #Create a directory to store the reports
                        checkFolderPath(tool["name"])
                        launchCmd = tool["exec"] + " " + launchCmd
                        #Substitute any environment variables
                        launchCmd = substituteArgs(remaining_argv, launchCmd)
                        print "*****************************"
                        print "Launch: " + launchCmd
                        print "*****************************"
                        if not test_mode:
                            call(shlex.split(launchCmd))

                    #Execute a pre-commmand, such as a setup or update requirement
                    if tool["post"] is not None:
                        if not test_mode:
                            call(shlex.split(tool["post"]))
                else:
                    print "Profile or command to run not found in configuration file."
            else:
                print "No profile or scan type found."

        except yaml.YAMLError as exc:
            print(exc)
