import os, json, argparse, subprocess, sys
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
)

OPENAI_API_KEY = client.api_key
sys.stdout = open('/dev/tty', 'w')

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



def new_labels_needed(labels, url, title, description):
    adequate_labels_query = f"""Given the following bookmark:
    url: {url}
    title: {title}
    description: {description}

Are new labels needed to adequately delineate the broad categories and topics of the bookmark? (True) or can you label it accurately with the existing labels? (False)
Only answer True if you are certain that new labels are needed. If you are unsure, then answer False.
Only reply with True or False.

    **labels:**
    {labels}

**Important**: Say nothing except true or false."""
    messages = [
        {"role": "system", "content": """You are a helpful assistant designed to answer binary questions with True or False."""},
        {"role": "user", "content": adequate_labels_query}
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        temperature=0,
        seed=0,
        messages=messages,
    )
    response_message = response.choices[0].message
    print(f"New Labels Are Needed: {response_message.content}")
    if response_message.content == "True":
        return True
    else:
        return False


def generate_new_labels(labels, url, title, description):
    """Generate new labels if the existing labels are inadequate."""
    messages = [
        {"role": "system", "content": """You are a helpful assistant designed to output correct JSON lists of labels in the JSON format: {"label": "description", "label": "description"}
         **IMPORTANT** Pay close attention to unfamiliar words and phrases, they may be very important and delineate a new concept."""},
        {"role": "user", "content": f"""Think of some keywords for this link.\n
         url: {url}\n
         title: {title}\n
         description: {description}\n
         
         **labels:**
         {labels}\n
        Write A MAXIMUM OF TWO NEW label,description pairs to describe this link, as the existing labels are not adequate on their own.
        *IMPORTANT* Make sure the labels are useful. They should capture the topics of the link, not the link itself.
        They should also be in keeping with the style of the existing labels.
        Keep descriptions short and to the point. They should be no longer than a sentence."""}
    ]
    # Step 1: call the model
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        temperature=1,
        seed=0,
        messages=messages,
    )
    response_message = response.choices[0].message
    return response_message


def pick_labels_new_tools_api(url, title, description, repo="irthomasthomas/undecidability", labels=None, generated_labels=None, labels_dict=None):
    """
    Use the new tool_calls API to decide when labels are needed and pick the labels.
    """
    tools = [
        # Tool definition for getting GitHub issue labels
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
        # Tool definition for assigning GitHub issue labels (unused)
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
            }
        }
    ]

    pick_labels_query = f"""I use GH issues as bookmarks. Given the following bookmark:\n
        repo: {repo}\n
        url: {url}\n
        title: {title}\n
        description: {description}\n
        
        Which, if any, of these gh labels certainly apply to this bookmark?
        *IMPORTANT* Only pick from the labels provided if they apply. Output a JSON list of labels.
        *IMPORTANT* if no labels apply, output an empty list or select the 'New Label' label exclusively to request a new label be made to categorize this bookmark.
            
        **labels:**
        {labels}

        **IMPORTANT** Only say from the labels under the **labels:** heading. Do not say anything else
        """

    messages = [
        {"role": "system", "content": """You are a helpful JSON assistant primed to write JSON lists of labels. 
         You always pay very close attention to writing syntactically correct JSON at all times.
        Think carefully about the labels you reply with. 
        The labels you select should make it easier to delineate and organize the information without being too specific.
         **IMPORTANT**: Only pick from the labels provided by the user."""},
        {"role": "user", "content": pick_labels_query}
    ]
    print("calling the model")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        temperature=1,
        seed=1234,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if tool_calls:
        messages.append(response_message)
        print("there were tool_calls")
        for tool_call in tool_calls:
            print(f"tool_call: {tool_call}")
            if tool_call.function.name == "get_issues_labels_list":
                function_args = json.loads(tool_call.function.arguments)
                labels = request_labels_list(function_args["repo"])
                # print(f"labels: {labels}") # Ok up to here
                print()
                messages.append(
                    {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": labels
                    }
                )
        # Ok to here.
        print(f"messages: {messages}")
        second_response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            temperature=1,
            seed=1234,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        second_response_message = second_response.choices[0].message
        tool_calls = second_response_message.tool_calls
        generated_labels = json.loads(tool_calls[0].function.arguments)['labels']
        checked_labels = []
        # check if generated_labels are in labels, if not, delete them.
        for label in generated_labels:
            if label in labels:
                checked_labels.append(label)
        print(f"checked_labels: {checked_labels}")
        print()
        return checked_labels       

    else:
        raise Exception("No tool calls were made.")

parser = argparse.ArgumentParser(description='Generate labels for a given bookmark.')
parser.add_argument('--url', metavar='url', type=str, help='The url of the bookmark.')
parser.add_argument('--title', metavar='title', type=str, help='The title of the bookmark.')
parser.add_argument('--description', metavar='description', type=str, help='The selected text of the bookmark.')
parser.add_argument('--repo', metavar='repo', type=str, help='The repo to get labels from.', default="irthomasthomas/undecidability")
args = parser.parse_args()

labels_dict = {}
generated_labels = None
if args.url:
    labels = request_labels_list(args.repo)
    if new_labels_needed(labels, args.url, args.title, args.description):
        generated_labels = generate_new_labels(labels, args.url, args.title, args.description)
        generated_labels_list = json.loads(generated_labels.content)

    picked_labels = pick_labels_new_tools_api(args.url, args.title, args.description, args.repo, labels, generated_labels, labels_dict)
    
    if generated_labels:
        labels_dict["generated_labels"] = generated_labels_list
    
    labels_dict["picked_labels"] = picked_labels
    print(f"labels_dict: {labels_dict}")
    sys.stdout = sys.__stdout__
    print(f"{json.dumps(labels_dict, indent=4)}")