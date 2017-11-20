#Jenkins Integration Notes

## Setting up a Jenkins WebHook

Create a user called API for example. Retrive the API token by logging in as that user.

Parameters are passed in the URI and access in the Pipeline script as follows:

Curl example:

```
curl -v -X POST http://<jenkinsuser>:<api_key>@localhost:8080/job/<job_name>/buildWithParameters --data token=<DEFINED_ON_JENKINS_JOB> --data TEST=work
```

Pipeline access

```
print "DEBUG: parameter TEST = ${TEST}"
print "DEBUG: parameter TEST PARAMS = ${params.TEST}"
```

Setting Global Variables and Secrets

### Manage Jenkins -> Configure System -> Global Properties

```
DefectDojo Host:
DOJO_HOST='http://dojo:8000'

${DOJO_HOST}

AppSpider
APPSPIDER_HOST='http://appspider'
```

### Jenkins -> Credentials -> System -> Global credentials

Dojo:
Secret text: DOJO_API_KEY : API_KEY

AppSpider:
Username/Password APPSPIDER_USERNAME : Username / Password
AdminUsername/Password APPSPIDER_ADMIN_USERNAME : Username / Password
