import os, json, argparse, subprocess, sys, requests
import numpy as np
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
)

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
        terminal_content += (f"Output token {i}: {logprob.token}, logprobs: {logprob.logprob}, linear probability: {np.round(np.exp(logprob.logprob)*100,2)}%\n")
        if np.round(np.exp(logprob.logprob)*100,2) > 99:
            print(f"New Label required: \033[1;32;40mTrue: {np.round(np.exp(logprob.logprob)*100,2)}\033[0m")
            return True
        elif np.round(np.exp(logprob.logprob)*100,2) > 95:
            print(f"New Label required: \033[1;33;40mTrue: {np.round(np.exp(logprob.logprob)*100,2)}\033[0m")
            return True
        elif np.round(np.exp(logprob.logprob)*100,2) > 90:
            print(f"New Label required: \033[1;31;40mTrue: {np.round(np.exp(logprob.logprob)*100,2)}\033[0m")
            return True
    return False


def generate_new_labels(labels, url, title, description):
    """Generate new labels if the existing labels are inadequate."""
    system_message = """
        You are a helpful assistant designed to output correct JSON lists of labels.
        Use the JSON format: {"label": "description", "label": "description"}.
        **IMPORTANT** Pay close attention to unfamiliar words and phrases, they may be very important to delineate a new concept.
    """
    user_query = f"""Think of some keywords for this link.\n
         url: {url}\n
         title: {title}\n
         description: {description}\n
         
         **labels:**
         {labels}\n
        Write A MAXIMUM OF TWO NEW label,description pairs to describe this link, as the existing labels are not adequate on their own.
        *IMPORTANT* Make sure the labels are useful. They should capture the topics of the link, not the link itself.
        They should also be in keeping with the style of the existing labels.
        Keep descriptions short and to the point. They should be no longer than a sentence.
    """
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_query}
    ]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        temperature=1,
        seed=0,
        messages=messages,
    )
    response_message = response.choices[0].message
    print(f"response_message: {response_message.content}")
    return response_message


def create_new_labels(repo, label_list):
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
    system_message = """
        You are a helpful assistant designed to output JSON lists of labels. 
        Think carefully about the labels you select. 
        The labels you select should make it easier to organize and search for information. 
         **IMPORTANT** Only pick from the labels provided."""
    pick_labels_query = f"""
    Given the following bookmark:\n
    url: {url}\n
    title: {title}\n
    description: {description}\n
    
    Which, if any, of these labels certainly apply to this bookmark?
    *IMPORTANT* Only pick from the labels provided if they apply. Output a JSON list of labels.
    *IMPORTANT* if no labels apply, output an empty list or select the 'New Label' label exclusively to request a new label be made to categorize this bookmark.
    *IMPORTANT* Request new labels sparingly.
    
    **existing labels:**
    
    {labels}

    **IMPORTANT** Only say from the labels under the **labels:** heading. Do not say anything else
    """

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": pick_labels_query}
    ]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        temperature=1,
        seed=0,
        messages=messages
    )
    
    picked_labels = response.choices[0].message.content
    if picked_labels:
        picked_labels_list = json.loads(picked_labels) 
        print(f"picked_labels_list: {picked_labels_list}")
        print()
        return picked_labels_list
        

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
    # NEW LABELS GENERATION
    if check_if_new_labels_needed(labels, args.url, args.title, args.description):
        generated_labels = generate_new_labels(labels, args.url, args.title, args.description)
        generated_labels_list = json.loads(generated_labels.content)
        if "New Label" not in picked_labels.keys():
            picked_labels["New Label"] = True

        labels_dict["generated_labels"] = generated_labels_list
    
    labels_dict["picked_labels"] = picked_labels
    sys.stdout = sys.__stdout__
    print(f"{json.dumps(labels_dict, indent=4)}")