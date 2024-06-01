import os
import sys
import xml.etree.ElementTree as ET
import re


class bcolors:
    OK = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    RESET = '\033[0m'
    INFO = '\033[94m'

def banner():
    print(""" ____  ____  __  ____  __    ____  _  _ 
(_  _)(  _ \(  )(  _ \(  )  (  __)( \/ )
  )(   )   / )(  ) __// (_/\ ) _)  )  ( 
 (__) (__\_)(__)(__)  \____/(____)(_/\_) by S1rN3tZ

""")

def help():
    print(bcolors.INFO+"[*]"+bcolors.RESET+" usage: echo path/to/appRepo/ | python3 triplex.py")

def find_android_manifest(repo_path):
    for root, dirs, files in os.walk(repo_path):
        if "AndroidManifest.xml" in files:
            return os.path.join(root, "AndroidManifest.xml")
    return None

def get_exported_components_with_intents(manifest_path):
    exported_components = []
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    namespace = {'android': 'http://schemas.android.com/apk/res/android'}

    components = ["activity", "receiver", "service"]

    for component in components:
        for elem in root.findall(f".//{component}", namespace):
            exported = elem.attrib.get('{http://schemas.android.com/apk/res/android}exported')
            if exported == "true" and has_intent_filter(elem):
                component_name = elem.attrib.get('{http://schemas.android.com/apk/res/android}name')
                exported_components.append({
                    "component_type": component,
                    "component_name": component_name,
                })

    return exported_components

def has_intent_filter(component):
    return component.find('intent-filter') is not None

def find_smali_files(repo_path, components):
    smali_paths = []

    for component in components:
        component_name = component['component_name']
        component_path = component_name.replace('.', '/')
        smali_file_path = os.path.join(repo_path, 'smali', f"{component_path}.smali")
        
        if os.path.exists(smali_file_path):
            smali_paths.append({
                "component_name": component_name,
                "path": smali_file_path
            })

    return smali_paths

def extract_extras(smali_files):
    regex_match = re.compile(r"const-string v\d+, \"(?P<extra>.*?)\"\s+invoke-virtual \{.*?\}, Landroid/content/Intent;->(?P<method>get[A-Za-z]+Extra|putExtra)")

    component_intents = {}

    for smali_file in smali_files:
        component_name = smali_file['component_name']
        file_path = smali_file['path']

        if component_name not in component_intents:
            component_intents[component_name] = {'Methods': [], 'Extras': []}

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = regex_match.finditer(content)

            for match in matches:
                extra = match.group('extra')
                method = match.group('method')
                if method not in component_intents[component_name]['Methods']:
                    component_intents[component_name]['Methods'].append(method)
                if extra not in component_intents[component_name]['Extras']:
                    component_intents[component_name]['Extras'].append(extra)

    return component_intents

def main():
    banner()
    repo_path = sys.stdin.read().strip()
    if not os.path.exists(repo_path):
        print(bcolors.WARNING+"[!]"+bcolors.RESET+" Repository path does not exist.")
        help()
        sys.exit(1)
    
    manifest_path = find_android_manifest(repo_path)
    if not manifest_path:
        print(bcolors.WARNING+"[!]"+bcolors.RESET+" AndroidManifest.xml not found.")
        help()
        sys.exit(1)
    
    exported_components = get_exported_components_with_intents(manifest_path)
    if not exported_components:
        print(bcolors.WARNING+"[!]"+bcolors.RESET+" No exported components with intents found.")
        help()
        sys.exit(1)

    smali_files = find_smali_files(repo_path, exported_components)
    if not smali_files:
        print(bcolors.WARNING+"[!]"+bcolors.RESET+" No smali files found.")
        help()
        sys.exit(1)

    component_intents = extract_extras(smali_files)
    
    for component in exported_components:
        component_name = component['component_name']
        print(bcolors.OK+"[+]"+bcolors.RESET+f" Exported {component['component_type'].capitalize()}: "+bcolors.OK+f"{component_name}"+bcolors.RESET)
        if component_intents.get(component_name):
            if component_intents[component_name]['Methods']:
                print(bcolors.INFO+"    [*]"+bcolors.RESET+" Extras Methods:")
                for method in component_intents[component_name]['Methods']:
                    print("        |_ "+bcolors.INFO+f"{method}"+bcolors.RESET)
            if component_intents[component_name]['Extras']:
                print(bcolors.INFO+"    [*]"+bcolors.RESET+" Extras keys:")
                for extra in component_intents[component_name]['Extras']:
                    print("        |_ "+bcolors.INFO+f"{extra}"+bcolors.RESET)
        print()

if __name__ == "__main__":
    main()
