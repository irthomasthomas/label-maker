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
    # Step 1: call the model
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


#  Think carefully about the labels you choose. Only output labels in json format.
        # The labels you create should make it easier to organize and retrieve information by topic and genre.
        #  They should also be in keeping with the style of the existing labels.
        #  never create labels for company names, people, or other proper nouns.


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
    """
    Choose the labels to assign to a bookmark.
    """
    
    pick_labels_query = f"""Given the following bookmark:\n
    url: {url}\n
    title: {title}\n
    description: {description}\n
    
    Which, if any, of these labels certainly apply to this bookmark?
    *IMPORTANT* Only pick from the labels provided if they apply. Output a JSON list of labels.
    *IMPORTANT* if no labels apply, output an empty list or select the 'New Label' label exclusively to request a new label be made to categorize this bookmark.
        
    **labels:**
    
    
    {labels}


    **IMPORTANT** Only say from the labels under the **labels:** heading. Do not say anything else
    """

    messages = [
        {"role": "system", "content": """You are a helpful assistant designed to output JSON lists of labels. 
        Think carefully about the labels you select. 
        The labels you select should make it easier to organize and search for information. 
         **IMPORTANT** Only pick from the labels provided."""},
        {"role": "user", "content": pick_labels_query}
    ]
    # Step 1: call the model
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        temperature=1,
        seed=0,
        messages=messages
    )
    
    picked_labels = response.choices[0].message.content
    if picked_labels:
        picked_labels_list = json.loads(picked_labels) # picked_labels_list: {'Models': True, 'llm': True, 'prompt': True, 'few-shot-learning': True}
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

if args.url:
    labels = request_labels_list(args.repo)
    print(f"labels count: {len(labels)}")
    if new_labels_needed(labels, args.url, args.title, args.description):
        generated_labels = generate_new_labels(labels, args.url, args.title, args.description)
        generated_labels_list = json.loads(generated_labels.content)

    picked_labels = pick_labels(args.url, args.title, args.description, labels) # picked_labels_list: {'MachineLearning': 'ML Models, Training and Inference', 'AI-Agents': 'Autonomous AI agents using LLMs', 'GoogleCloud': 'Google Cloud-related content'}
    if generated_labels:
        if "New Label" not in picked_labels.keys():
            picked_labels["New Label"] = True

        labels_dict["generated_labels"] = generated_labels_list
    
    labels_dict["picked_labels"] = picked_labels
    sys.stdout = sys.__stdout__
    print(f"{json.dumps(labels_dict, indent=4)}")