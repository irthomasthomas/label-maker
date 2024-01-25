import os, json, argparse, subprocess, sys, requests
import numpy as np
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
)

if os.name == 'nt':
    sys.stdout = open('CON', 'w')
else:
    sys.stdout = open('/dev/tty', 'w')

print(f"openai version: {client._version}")

def request_labels_list(repo):
    with open('/dev/tty', 'w') as f:
        f.write(f"get_issues_labels_list: {repo}\n\n")
        per_page = 100
        command = ["gh", "label", "list", "-R", repo, "-L", "100", "--json", "name,description,color"]
        
        # Execute the command using subprocess
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        labels = json.loads(result.stdout)
        if labels:
            f.write(f"got {len(labels)} labels\n\n")
        
        if result.stderr:
            print("Error:", result.stderr)
        parsed_labels = ""
        label_dict = {}
        
        for label in labels:
            parsed_labels += f"{label['name']}: {label['description']}\n"
        return parsed_labels


def check_if_new_labels_needed(labels, url, title, description):
    terminal_content = ""

    system_message = """You are a helpful assistant designed to answer binary questions with True or False."""

    adequate_labels_query = f"""
        Given the following bookmark:
        url: {url}
        title: {title}
        description: {description}

        Are new labels needed to adequately delineate the broad categories and topics of the bookmark? (True) or can you label it accurately with the existing labels? (False)
        Only answer True if you are certain that new labels are needed. 
        If you are unsure, then answer False.
        New labels should be used sparingly when the increase the information content of the object.
        Only reply with True or False.

        **labels:**
        {labels}

        **Important**: Say nothing except true or false."""
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": adequate_labels_query}
    ]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        temperature=0,
        seed=1234,
        max_tokens=1,
        messages=messages,
        logprobs=True,
        top_logprobs=2,
    )  
    
    top_two_logprobs = response.choices[0].logprobs.content[0].top_logprobs
    for i, logprob in enumerate(top_two_logprobs, start=1): 
        confidence = np.round(np.exp(logprob.logprob)*100,2)
        if logprob.token == "True":
            if confidence > 99:
                print(f"New Label required: \033[1;32;40mTrue: {confidence}\033[0m")
                return True,confidence
            elif confidence > 98:
                print(f"New Label required: \033[1;33;40mTrue: {confidence}\033[0m")
                return True,confidence
            else:
                return True,confidence
        elif logprob.token == "False":
            if confidence > 99:
                print(f"New Label required: \033[1;30;40mFalse: {confidence}\033[0m")
                return False,confidence
            elif confidence > 98:
                print(f"New Label required: \033[1;35;40mFalse: {confidence}\033[0m")
                return False,confidence
            else:
                print(f"New Label required: \033[1;31;40mFalse: {confidence}\033[0m")
                return False,confidence
    return False,0


def generate_new_labels(labels, url, title, description):
    """Generate new labels if the existing labels are inadequate."""
    tools = [
        {
            "type": "function", #
            "function": {
                "name": "create_new_label",
                "description": """Create a new label to delineate the content. Think carefully and choose labels wisely.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "label-name": {
                            "type": "string",
                            "description": "label-name."},
                        "description": {
                            "type": "string",
                            "description": "The description of the label."},
                        "repo": {
                            "type": "string",
                            "description": "The repo to create the label in."},
                    },
                    "required": ["label-name", "description", "repo"],
                },
            },
        },
    ]
    system_message = """
        You are a helpful assistant designed to output correct JSON lists of labels.
        Use the JSON format: {"label": "description", "label": "description"}.
        **IMPORTANT** Pay close attention to unfamiliar words and phrases, they may be very important to delineate a new concept.
    """
    user_query = f"""Think of some keywords for this link.\n
         url: {url}\n
         title: {title}\n
         description: {description}\n
         
         **current labels:**
         {labels}\n

        Write A MAXIMUM OF TWO NEW label,description pairs to describe this link.
        *IMPORTANT* Make sure the labels are useful. They should delineate the topic without being overly specific.
        They should also be in keeping with the style of the existing labels.
        Keep descriptions short and to the point. They should be no longer than a sentence.
    """
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_query}
    ]
    max_retries = 3
    while max_retries > 0:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            temperature=1,
            seed=1234,
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "create_new_label"}},
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        function_name = tool_calls[0].function.name
        if not function_name == "create_new_label":
            max_retries -= 1
            continue
        else:
            function_args = json.loads(tool_calls[0].function.arguments)
            return function_args
    raise Exception("Failed to get labels")


def create_new_gh_issues_labels(repo, label_list):
    """Create new labels for a GitHub repo."""
    new_labels_created = []
    for label in label_list:
        label_name = label["name"]
        label_description = label["description"]
        command = ["gh", "label", "create", "-R", repo, label_name, "-d", label_description]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.stderr:
            print("Error:", result.stderr)
        else:
            print(f"Created label: {label_name}")
            new_labels_created.append(label_name)
    
    return new_labels_created


def pick_labels(url, title, description, labels):
    """    Choose the labels to assign to a bookmark.    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "assign_content_labels",
                "description": "Save a list of labels picked to delineate content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "label_name": {
                            "type": "string",
                            "description": "A list of label names."},
                    },
                    "required": ["label_name"],
                },
            },
        },
    ]
    system_message = """
        You are a helpful assistant designed to label text. 
        Think carefully about the labels you select. 
        The labels you select should make it easier to organize and search for information.
         **IMPORTANT** Only pick from the labels here given."""
    pick_labels_query = f"""
    Given the following content:\n
    url: {url}\n
    title: {title}\n
    description: {description}\n
    
    Which, if any, of these labels certainly apply to this content?
    *IMPORTANT* Only pick up to FIVE labels from the labels provided if they apply.
    
    **existing labels:**
    
    {labels}

    **IMPORTANT** Only say A MAXIMUM OF FIVE labels from the labels under the **labels:** heading. Do not say anything else
    """

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": pick_labels_query}
    ]
    max_retries = 3
    while max_retries > 0:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            temperature=1,
            seed=0,
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "assign_content_labels"}},
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        function_name = tool_calls[0].function.name
        if not function_name == "assign_content_labels":
            max_retries -= 1
            continue
        else:
            picked_labels = json.loads(tool_calls[0].function.arguments)
            picked_labels_list = picked_labels['label_name'].split(",")
            print(f"picked_labels_list: {picked_labels_list}")
            missing_labels = {}
            for picked_label in picked_labels_list:
                if picked_label not in labels:
                    picked_labels_list.remove(picked_label)
                    missing_labels[picked_label] = "missing"
            checked_labels = {}
            checked_labels['label_name'] = ",".join(picked_labels_list)
            checked_labels['missing_labels'] = missing_labels
            
            
            return checked_labels

        
    raise Exception("Failed to get labels")


parser = argparse.ArgumentParser(description='Generate labels for a given bookmark.')
parser.add_argument('--url', metavar='url', type=str, help='The url of the bookmark.')
parser.add_argument('--title', metavar='title', type=str, help='The title of the bookmark.')
parser.add_argument('--description', metavar='description', type=str, help='The selected text of the bookmark.')
parser.add_argument('--repo', metavar='repo', type=str, help='The repo to get labels from.', default="irthomasthomas/undecidability")
args = parser.parse_args()

labels_dict = {}
generated_labels = None
if args.url:
    # EXISTING LABELS
    labels = request_labels_list(args.repo)
    # PICK LABELS
    picked_labels = pick_labels(args.url, args.title, args.description, labels)
    print(picked_labels)
    # NEW LABELS GENERATION
    labels_needed, confidence = check_if_new_labels_needed(labels, args.url, args.title, args.description)
    if labels_needed:
        generated_labels = generate_new_labels(picked_labels, args.url, args.title, args.description)
        generated_labels['confidence'] = confidence
        if confidence >= 99:
            labels_created = create_new_gh_issues_labels(args.repo, generated_labels)
            # add labels_created to picked_labels
            picked_labels['label_name'] = picked_labels['label_name'] + "," + ",".join(labels_created)
        print(f"generated_labels: {generated_labels}")
        if "New-Label" not in picked_labels['label_name']:
            picked_labels['label_name'] = picked_labels['label_name'] + ",New-Label"

        labels_dict["generated_labels"] = generated_labels
    
    labels_dict["picked_labels"] = picked_labels

    sys.stdout = sys.__stdout__
    print(f"{json.dumps(labels_dict, indent=4)}")
