import requests, os, json, argparse
from openai import OpenAI
import subprocess

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
)

EXISTING_LABELS = []
ALL_LABELS_PICKED = []
LABEL_DICT = {} 
ISSUE_OBJECT = {}
URL = ""
TITLE = ""
DESCRIPTION = ""
REPO = ""
new_labels_created = {}
existing_labels_picked = {}

def create_new_label(label, description, repo):
    print("create_new_label")
    # command = ["gh", "label", "create", "-R", repo, label, "-d", description]
    # result = subprocess.run(command, capture_output=True, text=True, check=True)
    # if result.stderr:
        # print("Error:", result.stderr)
    new_labels_created[label] = description
    return "Created new label."


def get_issues_labels_list(repo):
    global EXISTING_LABELS, LABEL_DICT
    print("get_issues_labels_list")
    labels_url = f"https://api.github.com/repos/{repo}/labels?per_page=10"  # Increased per_page to a large number to fetch more labels if needed
    EXISTING_LABELS = requests.get(labels_url).json()
    
    for label in EXISTING_LABELS:
        LABEL_DICT[label['name']] = label['description']  # Populate LABEL_DICT with the existing labels from GitHub
    return ", ".join([f"{label['name']}: {label['description']}" for label in EXISTING_LABELS])


def assign_gh_issue_labels(labels):
    print("assign_gh_issue_labels")
    global ALL_LABELS_PICKED, EXISTING_LABELS, ISSUE_OBJECT, URL, TITLE, DESCRIPTION, REPO, existing_labels_picked
    print(f"LABEL_DICT before assignment: {LABEL_DICT}")  # Added this debug line
    print(f"Incoming labels to assign: {labels}")  # Added this debug line to show the labels being processed
    
    ALL_LABELS_PICKED = []
    existing_labels = set(LABEL_DICT.keys())  # Use a set for faster membership testing
    for label in labels:
        label = label.strip()  # Strip any whitespace from the label string
        if label.lower() in (name.lower() for name in existing_labels) or label in new_labels_created:
            ALL_LABELS_PICKED.append(label)
            if label in existing_labels:
                existing_labels_picked[label] = LABEL_DICT[label]
                print(f"Existing label picked: {label}")  # Added this debug line
        else:
            print(f"Label '{label}' not found.")  # Changed to reflect that label is not found in either

    ISSUE_OBJECT = {
        "title": TITLE,
        "description": DESCRIPTION,
        "url": URL,
        "repo": REPO,
        "labels": ALL_LABELS_PICKED
    }
    print(f"Labels finally picked: {ALL_LABELS_PICKED}")  # Added to show the result of label assignment
    return "Assigned labels."

def openai_pick_labels_function(url, title, description, repo="irthomasthomas/undecidability", labels=None, generated_labels=None, labels_dict=None):
    # Define tools for OpenAI API to use
    print("openai_pick_labels_function")
    global EXISTING_LABELS
    global ALL_LABELS_PICKED
    global LABEL_DICT
    global new_labels_created
    global existing_labels_picked

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_issues_labels_list",
                "description": "Get the list of gh issue labels for a given repo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "A gh repository to request issue labels for."},
                    },
                    "required": ["repo"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "assign_gh_issue_labels",
                "description": "Save a list of gh issue labels for the request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "labels": {
                            "type": "string",
                            "description": "A list of labels."},
                    },
                    "required": ["labels"],
                },
            },
        },
        {
            "type": "function", #
            "function": {
                "name": "create_new_label",
                "description": "Create a new label for the request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "The name of the label."},
                        "description": {
                            "type": "string",
                            "description": "The description of the label."},
                        "repo": {
                            "type": "string",
                            "description": "The repo to create the label in."},
                    },
                    "required": ["label", "description", "repo"],
                },
            },

        }
    ]
        
    print("# Query for assigning labels without a provided list")
    user_query = f"""What gh issue labels should I assign to this bookmark?
url: {url}
title: {title}
description: {description}
gh_repo: {repo}"""

    messages = [
        {"role": "system", "content": """You are a helpful assistant designed to output JSON lists of labels. 
         You will be required to pick labels from a list of labels provided. 
         You may also be required to create new labels, if the existing labels are not sufficient.
         The labels you select should make it easier to delineate the content and organise the information.
         If you need the labels for a repo, call the get_issues_labels_list function."""},
        {"role": "user", "content": user_query}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        temperature=0,
        seed=0,
        messages=messages,
        tools=tools,
        tool_choice="auto"  
    )

    response_message = response.choices[0].message
    messages.append(response_message)
    if response_message.tool_calls:
        tool_calls = response_message.tool_calls
    else:
        tool_calls = None

    eventually_created_label = ""
    while tool_calls:
        available_functions = {
            "get_issues_labels_list": get_issues_labels_list,
            "create_new_label": create_new_label,
            "assign_gh_issue_labels": assign_gh_issue_labels,
        }
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            if function_name == "create_new_label":
                new_labels_created[function_args["label"]] = function_args["description"]
                function_response = "Created new label."
            elif function_name == "assign_gh_issue_labels":
                function_args["labels"] = [x.strip() for x in function_args["labels"].split(",")]
                function_response = function_to_call(**function_args)
            else:
                function_response = function_to_call(**function_args)
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )

        second_response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            temperature=0,
            seed=1234,
            messages=messages,
            tools=tools,
            tool_choice="auto"  
        )
        if second_response.choices[0].message.tool_calls:
            tool_calls = second_response.choices[0].message.tool_calls
            messages.append(second_response.choices[0].message)
        else:
            tool_calls = None

    result = {
        "new_labels_created": new_labels_created,
        "existing_labels_picked": existing_labels_picked,
    }

    if eventually_created_label:
        result["new_labels_created"][eventually_created_label] = response_message.content.split("New label created: ")[1]

    return result

parser = argparse.ArgumentParser(description='Generate labels for a given bookmark.')
parser.add_argument('--url', metavar='url', type=str, help='The url of the bookmark.')
parser.add_argument('--title', metavar='title', type=str, help='The title of the bookmark.')
parser.add_argument('--description', metavar='description', type=str, help='The selected text of the bookmark.')
parser.add_argument('--repo', metavar='repo', type=str, help='The repo to get labels from.', default="irthomasthomas/undecidability")
args = parser.parse_args()

# test create_new_label
create_new_label("test_label", "test_description", "irthomasthomas/undecidability")

while True:
    try:
        checked_labels = openai_pick_labels_function(args.url, args.title, args.description, args.repo)
        LABEL_DICT = {label: desc for label, desc in new_labels_created.items()}
        LABEL_DICT.update({label: desc for label, desc in existing_labels_picked.items()})
    except Exception as e:
        print(e)
        continue
    if checked_labels:
        print(json.dumps(checked_labels, indent=4))
        break
    else:
        continue