import argparse
import yaml
import os
from cryptography.fernet import Fernet

def getKey(key=None):
    if key == None:
        key = Fernet.generate_key()
    else:
        key = key

    return key

def encrypt(key, data):
    f = Fernet(key)
    token = f.encrypt(data)
    return token

def decrypt(key, data):
    f = Fernet(key)
    token = f.decrypt(data)
    return token

def parseAuthFile(authFile, crypto, key=None, toolName=None):

    if key is None:
        key = getKey()
        #write the key file out
        secretFile = os.path.basename(authFile)
        secretFile = os.path.join(os.path.dirname(authFile), os.path.splitext(secretFile)[0]+ ".key")

        print "Key file: " + secretFile
        f = open(secretFile,"w")
        f.write(key)
        f.close()

    print "Crypto: " + crypto
    if authFile is not None:
        with open(authFile, 'r') as stream:
            try:
                #Tool configuration
                tools = yaml.safe_load(stream)
                for tool in tools:
                    toolParms = tools[tool]["parameters"]
                    if toolName is None or tool == toolName:
                        parameters_key = {}
                        for parameter in toolParms:
                            if crypto == "encrypt":
                                toolParms[parameter]["value"] = encrypt(key, (toolParms[parameter]["value"]))
                            elif crypto == "decrypt":
                                toolParms[parameter]["value"] = decrypt(key, (toolParms[parameter]["value"]))
                #encrypt the file values
                print "Encrypted value text file: " + authFile
                with open(authFile, 'w') as f:
                    yaml.dump(tools, f, default_flow_style=False)

            except yaml.YAMLError as exc:
                print(exc)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    #Command line options
    parser.add_argument("-c", "--crypto", help="Encrypt or decrypt.", required=False, default="encrypt")
    parser.add_argument("-k", "--key", help="A URL-safe base64-encoded 32-byte key file.", required=False, default=None)
    parser.add_argument("-a", "--auth", help="Tool configuration credentials and or API keys.", required=False, default=None)
    parser.add_argument("-t", "--tool", help="Encryption action on just one tool.", required=False, default=None)

    args, remaining_argv = parser.parse_known_args()

    key = args.key
    if key is not None:
        keyFile = open(key,"r")
        key = keyFile.read()
        keyFile.close

    if args.auth:
        parseAuthFile(args.auth, args.crypto, key=key)
