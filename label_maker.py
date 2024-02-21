import os
import json
import argparse
import sys
import requests
import numpy as np
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
)

if os.name == 'nt':
    sys.stdout = open('CON', 'w')
else:
    sys.stdout = open('/dev/tty', 'w')

print(f"openai version: {client._version}")


def gh_api_request(repo, method="GET", endpoint="", data=None):
    """
    General-purpose GitHub API request function.
    
    :param repo: Repository name including the owner (e.g., "owner/repo")
    :param method: HTTP method (e.g., "GET", "POST")
    :param endpoint: API endpoint after the repo URL (e.g., "/labels")
    :param data: Data payload for POST requests
    :return: Response object
    """
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{repo}{endpoint}"
    
    if method.upper() == "GET":
        response = requests.get(url, headers=headers)
    elif method.upper() == "POST":
        response = requests.post(url, json=data, headers=headers)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    return response


def request_labels_list(repo):
    """
    Requests the list of labels for a given repository.

    Args:
        repo (str): The name of the repository.

    Returns:
        list: A list of labels if the request is successful, otherwise an empty list.
    """
    response = gh_api_request(repo, endpoint="/labels?per_page=100")
    if response.ok:
        labels = response.json()
        print(f"Got {len(labels)} labels")
        return labels
    else:
        print(f"Failed to get labels: {response.text}")
        return []


def create_new_labels(repo, label_list):
    """
    Creates new GitHub issues labels for a given repository.

    Args:
        repo (str): The name of the repository.
        label_list (list): A list of dictionaries containing label information.

    Returns:
        list: A list of label names that were successfully created.
    """
    new_labels_created = []
    for label in label_list:
        label_name = label["name"]
        label_description = label.get("description", "")  # Use .get() to avoid KeyError if 'description' is missing
        data = {
            "name": label_name,
            "description": label_description,
            "color": "f29513",  # Consider dynamically setting or randomizing color
        }
        response = gh_api_request(repo, method="POST", endpoint="/labels", data=data)
        if response.ok:
            print(f"Created label: {label_name}")
            new_labels_created.append(label_name)
        else:
            print(f"Failed to create label {label_name}: {response.text}")
    return new_labels_created


@retry(stop=stop_after_attempt(8), wait=wait_random_exponential(multiplier=1, max=60))
def check_if_new_labels_needed(current_labels, page_url, page_title, page_snippet):
    
    system_message = """You are a helpful assistant designed to answer binary questions with True or False."""

    adequate_labels_query = f"""
        Given the following bookmark:
        url: {page_url}
        title: {page_title}
        snippet: {page_snippet}

        Are new labels needed to adequately delineate the broad categories and topics of the bookmark? (True) or can you label it accurately with the existing labels? (False)
        Only answer True if you are certain that new labels are needed. 
        If you are unsure, then answer False.
        New labels should be used sparingly when the increase the information content of the object.
        Only reply with True or False.

        **labels:**
        {current_labels}

        **Important**: Say nothing except true or false."""
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": adequate_labels_query}
    ]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
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


@retry(stop=stop_after_attempt(8), wait=wait_random_exponential(multiplier=1, max=60))
def generate_new_labels(current_labels, page_url, page_title, page_snippet):
    """Generate new labels if the existing labels are inadequate."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "create_new_label",
                "description": "Create a new label to delineate the content. Think carefully and choose labels wisely.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "label-name": {
                            "type": "string",
                            "description": "label-name."},
                        "label-description": {
                            "type": "string",
                            "description": "A brief description for the label."},
                        "gh-repo": {
                            "type": "string",
                            "description": "The gh repo to create the label in."},
                    },
                    "required": ["label-name", "label-description", "gh-repo"],
                },
            },
        },
    ]
    system_message = """
        You are a helpful assistant designed to output correct JSON lists of labels.
        Use the JSON format: {"label": "description", "label": "description"}.
        **IMPORTANT** When thinking of new labels, pay close attention to unfamiliar words and phrases in the content to be labeled, they may be very important to delineate what is interesting about this content.
    """
    user_query = f"""Think of some keywords for this link.\n
         url: {page_url}\n
         title: {page_title}\n
         description: {page_snippet}\n
         
         **current labels:**
         {current_labels}\n

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
            model="gpt-3.5-turbo-0125",
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


@retry(stop=stop_after_attempt(8), wait=wait_random_exponential(multiplier=1, max=60))
def pick_labels(page_url, page_title, page_snippet, labels):
    """
    Choose the labels to assign to a bookmark, with improved handling for different formats.
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "assign_labels",
                "description": "Save a list of labels to cleanly delineate the content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "label_names": {
                            "type": "string",
                            "description": "A list of labels, e.g. source-code,Papers,RAG,New-Label"},
                    },
                    "required": ["label_names"],
                },
            },
        },
    ]
    system_message = """
        You are a helpful assistant designed to label text.
        Think carefully about the labels you select.
        The labels you select should make it easier to organize the information and delineate the content.
         **IMPORTANT** Pay attention to ALL labels and Only pick from the labels here given."""
    pick_labels_query = f"""
    <content>
    <url>{page_url}</url>

    <title>{page_title}</title>

    <description>{page_snippet}</description>
    </content>

    <instructions>Do any of these labels certainly apply to this content?
    *IMPORTANT* Pick about six labels from the labels_list if they apply. Look at and consider ALL of the labels.
    First write the labels you think apply, then call the function with the labels you have finally chosen in a CSV list.
    </instructions>

    <labels_list>
    
    {labels}
    
    </labels_list>
    """

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": pick_labels_query}
    ]
    max_retries = 6
    while max_retries > 0:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            temperature=0.9,
            seed=0,
            messages=messages,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "assign_labels"}},
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        function_name = tool_calls[0].function.name
        if not function_name == "assign_labels":
            max_retries -= 1
            continue
        else:
            picked_labels = json.loads(tool_calls[0].function.arguments)

            picked_labels_list = [label.strip().lower() for label in picked_labels['label_names'].split(",")]
            
            # Extract and clean existing label names to ensure accurate comparison
            existing_labels = [label['name'].lower().strip() for label in labels]            
            valid_picked_labels = [label for label in picked_labels_list if label in existing_labels]
            missing_labels = {label: "missing" for label in picked_labels_list if label not in valid_picked_labels}
            checked_labels = {}
            checked_labels['label_names'] = ",".join(valid_picked_labels)
            checked_labels['missing_labels'] = missing_labels
            return checked_labels
    raise Exception("Failed to get labels")


@retry(stop=stop_after_attempt(8), wait=wait_random_exponential(multiplier=1, max=60))
def generate_labels(page_url, page_title, page_snippet, target_repo):
    """
    Generates labels for a given page based on its URL, title, and snippet.

    Args:
        page_url (str): The URL of the page.
        page_title (str): The title of the page.
        page_snippet (str): The snippet of the page.
        target_repo (str): The target repository to generate labels for.

    Returns:
        dict: A dictionary containing the generated labels and the picked labels.
    """
    
    labels_dict = {}
    generated_labels = None

    # EXISTING LABELS
    MAX_RETRIES = 3
    while MAX_RETRIES > 0:
        MAX_RETRIES -= 1
        try:
            original_labels = request_labels_list(target_repo)
            label_mapping = {label['name'].lower(): label['name'] for label in original_labels}
            picked_labels = pick_labels(page_url, page_title, page_snippet, original_labels)
            picked_labels['label_names'] = ",".join([label_mapping[label] for label in picked_labels['label_names'].split(",")]) 

            # NEW LABELS GENERATION
            labels_needed, confidence = check_if_new_labels_needed(original_labels, page_url, page_title, page_snippet)
            if labels_needed:
                generated_labels = generate_new_labels(picked_labels, page_url, page_title, page_snippet)
                generated_labels['confidence'] = confidence
                if confidence >= 99:
                    labels_created = create_new_labels(target_repo, generated_labels)
                    picked_labels['label_names'] = picked_labels['label_names'] + "," + ",".join(labels_created)

                if "New-Label" not in picked_labels['label_names']:
                    picked_labels['label_names'] = picked_labels['label_names'] + ",New-Label"

                labels_dict["generated_labels"] = generated_labels
            
            labels_dict["picked_labels"] = picked_labels

            return labels_dict
        except Exception as e:
            print(e)
            continue



parser = argparse.ArgumentParser(description='Generate labels for a given bookmark.')
parser.add_argument('--url', metavar='url', type=str, help='The url of the bookmark.')
parser.add_argument('--title', metavar='title', type=str, help='The title of the bookmark.')
parser.add_argument('--snippet', metavar='snippet', type=str, help='The selected text of the bookmark.')
parser.add_argument('--repo', metavar='repo', type=str, help='The repo to get labels from.', default="irthomasthomas/undecidability")


if __name__ == "__main__":
    args = parser.parse_args()
    labels = generate_labels(args.url, args.title, args.description, args.repo)
    sys.stdout = sys.__stdout__
    print(f"{json.dumps(labels, indent=4)}")