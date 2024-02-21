#!/home/thomas/Development/Projects/llm/.venv/bin/python3

import json
from math import exp
import shlex
import subprocess
from llm import Collection, get_model
import os
import argparse
import logging
import sqlite_utils
from label_maker import gh_api_request, generate_labels
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
)


def logprobs_duplicate_check():
    """Use logprobs to check for duplicates."""
    system_message = f"""You are a helpful assistant trained to answer binary questions with True or False.\nNEVER say anything else but True or False."""

    duplicate_query_prompt = f"""
        Are these links likely duplicates? True or False.
        RESULT ONE:
        {title}
                    
        {issue_body}
        END RESULT ONE
                    
        RESULT TWO:
        {result_title}
                    
        {result_body}
        END RESULT TWO
                    
        cosine similarity: {entry.score}
                    
        IMPORTANT: The text does not have to be identical to be a duplicate. It is enough if the content is nearly identical.
        ONLY ANSWER TRUE OR FALSE."""
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": duplicate_query_prompt}
    ]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=messages,
        temperature=0,
        seed=1234,
        max_tokens=1,
        logprobs=True,
        top_logprobs=2,
    )
    
    top_two_logprobs = response.choices[0].logprobs.content[0].top_logprobs
    for logprob in top_two_logprobs:
        print(f"{logprob.token}: {round(exp(logprob.logprob)*100,2)}%")


def format_md_hidden_note(note, title="Expand for details"):
    """
    Formats the hidden note for GitHub issues.

    Args:
        note (str): The note to format.

    Returns:
        str: The formatted note.
    """
    return f"<details>\n<summary>{title}</summary>\n\n{note}\n\n</details>"


def bookmark_to_gh_issues(page_title, labels, repo, body, draft=False):
    """Creates a GitHub issue based on the provided parameters.
    Args:
        page_title (str): The title of the page.
        labels (dict): The generated labels for the page.
        repo (str): The name of the GitHub repository.
        body (str): The body of the issue.
        draft (bool): Whether to create a draft issue or not.
    Returns:
        str: The URL of the created issue if successful, None otherwise.
    """
        
    picked_labels = labels['picked_labels']['label_names']
    issue_json = False
    if draft:
        create_draft_issue_gh_cli(repo, page_title, body, picked_labels)
    else:
        issue_json = create_github_issue(repo, page_title, body, picked_labels)
        logging.info(f"Issue created: {issue_json}")
    
    return issue_json


def gh_issue_formatter(page_title, page_url, page_snippet, new_label_note):
    model = get_model("gpt-3.5-turbo")
    model.key = os.getenv("OPENAI_API_KEY")
    if not page_title:
        page_title = model.prompt(f"generate a title from this url:{page_url}:quote:{page_snippet}", temperature=0.4).text()

    # Reformat description
    content = f"""TITLE:{page_title}
    DESCRIPTION:{page_snippet}
    URL:{page_url}"""
    
    description_prompt = f"""
    #Instructions
    - Reformat this into beautiful github flavour markdown (GFM).
    - Keep the wording exact. Only edit formatting.
    - Include the entire content.
    **IMPORTANT**:ADD NO ADDITIONAL COMMENTARY OR TEXT OF ANY KIND.
    /START_CONTENT:/
    {content}
    /END_CONTENT/
    """
    
    page_snippet = model.prompt(description_prompt, temperature=0.1).text()
    
    description_prompt = description_prompt.replace("{content}", content)

    task_list = f"- [ ] [{page_title}]({page_url})"
    
    suggested_labels = f"#### Suggested labels\n#### {new_label_note}"

    body = f"{task_list}\n\n{page_snippet}\n\n{suggested_labels}"
    return page_title,body


def create_draft_issue_gh_cli(gh_repo, issue_title, issue_body, issue_labels):
    """
    Creates a GitHub issue in the specified repository using the GitHub CLI and opens it in the browser.
    
    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_title (str): The title of the issue.
        issue_body (str): The body of the issue.
        issue_labels (str): A comma-separated string of labels for the issue.
    """
    # Todo: replace shell commands with http requests.
    # url: https://github.com/irthomasthomas/undecidability/issues/new?body=-+%5B+%5D+%5BMoE+models+explained%5D%28stackek.com%29%0A%0A%0A%23+MoE+models+explained%0A%0A%2A%2ATL%3BDR%2A%2A%0A%0A%2A%2AMoEs%3A%2A%2A%0A%0A-+Are+pretrained+much+faster+vs.+dense+models%0A-+Have+faster+inference+compared+to+a+model+with+the+same+number+of+parameters%0A-+Require+high+VRAM+as+all+experts+are+loaded+in+memory%0A-+Face+many+challenges+in+fine-tuning%2C+but+recent+work+with+MoE+instruction-tuning+is+promising%0A%0ALet%E2%80%99s+dive+in%21%0A%0A%2A%2AWhat+is+a+Mixture+of+Experts+%28MoE%29%3F%2A%2A%0A%0AThe+scale+of+a+model+is+one+of+the+most+important+axes+for+better+model+quality.+Given+a+fixed+computing+budget%2C+training+a+larger+model+for+fewer+steps+is+better+than+training+a+smaller+model+for+more+steps.%0A%0AMixture+of+Experts+enable+models+to+be+pretrained+with+far+less+compute%2C+which+means+you+can+dramatically+scale+up+the+model+or+dataset+size+with+the+same+compute+budget+as+a+dense+model.+In+particular%2C+a+MoE+model+should+achieve+the+same+quality+as+its+dense+counterpart+much+faster+during+pretraining.%0A%0ASo%2C+what+exactly+is+a+MoE%3F+In+the+context+of+transformer+models%2C+a+MoE+consists+of+two+main+elements%3A%0A%0A1.+Sparse+MoE+layers+are+used+instead+of+dense+feed-forward+network+%28FFN%29+layers.+MoE+layers+have+a+certain+number+of+%E2%80%9Cexperts%E2%80%9D+%28e.g.+8%29%2C+where+each+expert+is+a+neural+network.+In+practice%2C+the+experts+are+FFNs%2C+but+they+can+also+be+more+complex+networks+or+even+a+MoE+itself%2C+leading+to+hierarchical+MoEs%21%0A2.+A+gate+network+or+router%2C+that+determines+which+tokens+are+sent+to+which+expert.+For+example%2C+in+the+image+below%2C+the+token+%E2%80%9CMore%E2%80%9D+is+sent+to+the+second+expert%2C+and+the+token+%22Parameters%E2%80%9D+is+sent+to+the+first+network.+As+we%E2%80%99ll+explore+later%2C+we+can+send+a+token+to+more+than+one+expert.+How+to+route+a+token+to+an+expert+is+one+of+the+big+decisions+when+working+with+MoEs+-+the+router+is+composed+of+learned+parameters+and+is+pretrained+at+the+same+time+as+the+rest+of+the+network.%0A%0AURL%3A+%5Bstackek.com%5D%28https%3A%2F%2Fstackek.com%29%0A%0A%23%23%23%23+Suggested+labels%0A%23%23%23%23+%7B%27label-name%27%3A+%27Mixture+of+Experts%27%2C+%27label-description%27%3A+%27Explanation+of+MoE+models+and+their+advantages+in+model+training+and+inference+speed.%27%2C+%27confidence%27%3A+63.88%7D&labels=Algorithms%2Cllm%2CMachineLearning%2CModels%2CResearch%2Csparse-computation%2CNew-Label&title=MoE+models+explained
    
    issue_body = shlex.quote(issue_body)
    issue_title = shlex.quote(issue_title)
    issue_labels = shlex.quote(issue_labels)
    
    command = f"gh issue create --repo {gh_repo} --title {issue_title} --body {issue_body} --label {issue_labels} --web"
    
    print(f"command: {command}")
    subprocess.run(shlex.split(command))
    
    return


def gh_view_issue(issue_number, web=False, pretty_print=False):
    """
    View a GitHub issue.

    Args:
        issue_number (int): The number of the issue to view.
        web (bool, optional): If True, open the issue in a web browser. Defaults to False.
        pretty_print (bool, optional): If True, pretty print the output. Defaults to False.

    Returns:
        tuple: A tuple containing the title and body of the issue.
    """
    
    if pretty_print:
        subprocess.run(shlex.split(command)) # pretty print gh output
    elif web:
        command = f"gh issue view {issue_number} -R 'irthomasthomas/undecidability' --web && disown"
        subprocess.run(shlex.split(command))
    else:
        command = f"gh issue view {issue_number} -R 'irthomasthomas/undecidability' --json body,title"
        response = subprocess.run(shlex.split(command), capture_output=True)
        response_json = json.loads(response.stdout.decode())
        body = response_json["body"]
        title = response_json["title"]
        
        return (title, body)
    
    
def create_github_issue(gh_repo, issue_title, issue_body, issue_labels):
    """
    Creates a new GitHub issue in the specified repository.

    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_title (str): The title of the issue.
        issue_body (str): The body/content of the issue.
        issue_labels (str): A comma-separated string of labels for the issue.

    Returns:
        dict or None: A dictionary containing the JSON response of the created issue if successful,
        None otherwise.
    """

    logging.info(f"labels: {issue_labels}")
    data = {
        "title": issue_title,
        "body": issue_body,
        "labels": issue_labels.split(",")
    }
    logging.info(f"data: {data}")

    response = gh_api_request(gh_repo, method="POST", endpoint="/issues", data=data)
    if response.ok:
        return response.json()
    else:
        logging.error(f"Failed to create issue: {response.text}")
        return None
    

def fetch_all_gh_issues(gh_repo):
    """
    Fetches all issues from the specified GitHub repository.

    Args:
        gh_repo (str): The name of the GitHub repository.

    Returns:
        list: A list of all issues from the specified repository.
    """
    response = gh_api_request(gh_repo, method="GET", endpoint="/issues")
    if response.ok:
        return response.json()
    else:
        logging.error(f"Failed to fetch issues: {response.text}")
        return None
    

def gh_issue_update(gh_repo, issue_number, issue_title=None, issue_body=None, issue_labels=None):
    """
    Updates the specified GitHub issue with the provided parameters.
    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_number (int): The number of the issue to update.
        issue_title (str, optional): The title of the issue. Defaults to None.
        issue_body (str, optional): The body of the issue. Defaults to None.
        issue_labels (str, optional): A comma-separated string of labels for the issue. Defaults to None.
    Returns:
        bool: True if the issue was updated successfully, False otherwise.
    """
    
    if issue_title and issue_body and issue_labels:
        data = {
            "title": issue_title,
            "body": issue_body,
            "labels": issue_labels.split(",")
        }
    elif issue_title and issue_body:
        data = {
            "title": issue_title,
            "body": issue_body
        }
    elif issue_title:
        data = {
            "title": issue_title
        }
    elif issue_body:
        data = {
            "body": issue_body
        }
    elif issue_labels:
        data = {
            "labels": issue_labels.split(",")
        }
    else:
        logging.error("No content provided to update issue.")
        return False
          
    response = gh_api_request(gh_repo, method="PATCH", endpoint=f"/issues/{issue_number}", data=data)
    if not response.ok:
        logging.error(f"Failed to update issue: {response.text}")
    return response.ok


def gh_find_similar_issues(title, issue_body, related_threshold=0.8):
    """
    Find similar gh issues based on embeddings of the title and issue body.

    Args:
        title (str): The title of the issue.
        issue_body (str): The body of the issue.
        related_threshold (float, optional): The threshold for similarity score. Defaults to 0.8.

    Returns:
        list: A list of filtered results containing similar issues.
    """
    collection = "gh-issues"
    database = "/home/thomas/undecidability/agents/sql-agent/github-issues.db"
    if database:
        db = sqlite_utils.Database(database)
    else:
        db = sqlite_utils.Database("embeddings.db")
    collection_obj = Collection(collection, db, create=False)
    content = f"{title}\n\n{issue_body}"
    results = collection_obj.similar(content, 4)
    filtered_results = [entry for entry in results if entry.score > related_threshold]
    
    return filtered_results  
        

def gh_add_issue_comment(gh_repo, issue_number, comment):
    """
    Adds a comment to the specified GitHub issue.

    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_number (int): The number of the issue to update.
        comment (str): The comment to add to the issue.
    """
    data = {
        "body": comment
    }
    response = gh_api_request(gh_repo, method="POST", endpoint=f"/issues/{issue_number}/comments", data=data)
    if not response.ok:
        logging.error(f"Failed to add comment to issue: {response.text}")
    return response.ok


def generate_embedding_for_gh_issues(gh_repo, database):
    """Read all gh issues into a sqlite database and generate embeddings."""
    return None
    
    
parser = argparse.ArgumentParser(description='Generate labels for a given bookmark.')
parser.add_argument('--url', metavar='url', type=str, help='The url of the bookmark.')
parser.add_argument('--title', metavar='title', type=str, help='The title of the bookmark.')
parser.add_argument('--snippet', metavar='snippet', type=str, help='The selected text of the bookmark.')
parser.add_argument('--repo', metavar='repo', type=str, help='The repo to get labels from.', default="irthomasthomas/undecidability")
parser.add_argument('--draft', metavar='draft', type=bool, help='Create a draft issue.', default=False)

args = parser.parse_args()

# Configure logging to a file
logging.basicConfig(filename='/tmp/app.log', level=logging.INFO)
logging.info(f"args:\n{args}")
labels_json = generate_labels(args.url, args.title, args.snippet, args.repo)
print(f"labels_json: {labels_json}")
picked_labels = labels_json['picked_labels']['label_names']
try:
    generated_labels = labels_json['generated_labels']
except KeyError:
    generated_labels = ""

page_title, body = gh_issue_formatter(args.title, args.url, args.snippet, generated_labels)

related_issues = gh_find_similar_issues(page_title, body)
related_threshold = 0.85
dup_threshold = 0.94
duplicate=False
if related_issues:
    related_issues_md = "### Related issues\n"
    for entry in related_issues:
        if entry.score > dup_threshold:
            duplicate = True            
            gh_view_issue(entry.id, web=True)
        elif entry.score > related_threshold:
            entry_title, entry_body = gh_view_issue(entry.id)
            related_issues_md += f"""
### #{entry.id}: {entry_title}
<details><summary>### Details</summary>Similarity score: {round(entry.score, 2)}\n{entry_body}</details>\n
"""
            

if not duplicate:
    issue = bookmark_to_gh_issues(page_title, labels_json, args.repo, body, args.draft)
    if issue:
        url = issue['html_url']
        id = issue['number']
        os.system(f"nyxt {url}")
        if related_issues:
            gh_add_issue_comment(args.repo, id, related_issues_md)