import json
import requests

class Notify(object):
    """AppSecPipeline."""

    def __init__(self, slack_web_hook, channel, username, icon_emoji):
        self.slack_web_hook = slack_web_hook
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji

    def slackAlert(self, **kwargs):
        payload_json = json.dumps(kwargs)
        webhook_url = "https://hooks.slack.com/services/%s" % self.slack_web_hook

        try:
            response = requests.post(
                webhook_url, data=payload_json,
                headers={'Content-Type': 'application/json'}
            )
        except:
            print "Slack timeout..."

    def chatAlert(self, text):
        self.slackAlert(text=text, channel=self.channel, username=self.username, icon_emoji=self.icon_emoji)

    def chatPipelineStart(self, source, profile, args):
        slackTxt = "Security Pipeline Scan from *%s* using profile: *%s* \n" % (source, profile)
        self.chatAlert("*Starting:* " + slackTxt)

    def chatPipelineTools(self, pipeline):
        self.chatAlert("*Tools that will be run:* ")
        appSecPipeline = ""
        toolName = None
        for tool in pipeline:
            toolData =  pipeline[tool]
            toolName = toolData['tool']
            appSecPipeline += toolName + ", "

        self.chatAlert(">>>*AppSecPipeline:* " + appSecPipeline[:-2])

        return toolName

    def chatPipelineIndividualTools(self, execute, toolName):
        text = "Executing"
        if execute == False:
            text = "Skipping"
        self.chatAlert(">>>*" + text + ":* " + toolName)

    def chatPipelineToolComplete(self, toolName):
        self.chatAlert(">>>*Completed Execution:* " + toolName)

    def chatPipelineComplete(self):
        self.chatAlert("*Completed Pipeline Scan*")

    def chatPipelineMention(self, mention, text):
        self.chatAlert("*Attention Needed*: %s %s" % (mention, text))
