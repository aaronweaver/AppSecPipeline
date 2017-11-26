import os

secPipelineFile = "controller/secpipeline-config.yaml"

#Re-create the pipeline config file
os.remove(secPipelineFile)

for subdir, dirs, files in os.walk("tools"):
    for file in files:
        if file.lower().endswith("yaml"):
            yamlFile = os.path.join(subdir, file)

            #Read tool YAML
            with open(yamlFile, 'r') as toolYaml:
                yamlContent = toolYaml.read()

            #Write to secpipeline-config.yaml
            with open(secPipelineFile, 'a+') as file:
                file.write(yamlContent)
