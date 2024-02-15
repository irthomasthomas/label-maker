#!/home/thomas/Development/Projects/llm/.venv/bin/python3

import llm
import os
import argparse
import logging


from label_maker import gh_api_request, generate_labels


def gfm_hidden_note(note, title="Expand for details"):
    """
    Formats the hidden note for GitHub issues.

    Args:
        note (str): The note to format.

    Returns:
        str: The formatted note.
    """
    return f"<details>\n<summary>{title}</summary>\n\n{note}\n\n</details>"


def bookmark_to_gh_issues(page_title, page_url, page_snippet, labels, new_label_note, repo, draft=True):
    """
    Creates a GitHub issue based on the provided parameters.

    Args:
        page_title (str): The title of the page.
        page_url (str): The URL of the page.
        page_snippet (str): The snippet of the page content.
        labels (dict): A dictionary containing the picked labels.
        new_label_note (str): The generated labels in markdown format.
        repo (str): The repository to create the issue in.
        draft (bool): Whether to create a draft issue.

    Returns:
        str: The URL of the created GitHub issue.
    """
    
    model = llm.get_model("gpt-3.5-turbo")
    model.key = os.getenv("OPENAI_API_KEY")
    if not page_title:
        page_title = model.prompt(f"generate a title from this url:{page_url}:quote:{page_snippet}", temperature=0.1).text()

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
    
    
    description_prompt = description_prompt.replace("{content}", content)
    
    page_snippet = model.prompt(description_prompt, temperature=0.1).text()

    task_list = f"- [ ] [{page_title}]({page_url})"
    
    suggested_labels = f"#### Suggested labels\n#### {new_label_note}"

    body = f"{task_list}\n\n{page_snippet}\n\n{suggested_labels}"
    
    picked_labels = labels['picked_labels']['label_names']
    if draft:
        create_draft_issue_gh_cli(repo, page_title, body, picked_labels)
    else:
        issue_url = create_github_issue(repo, page_title, body, picked_labels)
    
    logging.info(f"Issue created: {issue_url}")
    
    return issue_url


def create_draft_issue_gh_cli(gh_repo, issue_title, issue_body, issue_labels):
    """
    Creates a GitHub issue in the specified repository using the GitHub CLI and opens it in the browser.
    
    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_title (str): The title of the issue.
        issue_body (str): The body of the issue.
        issue_labels (str): A comma-separated string of labels for the issue.
    """
    os.system(f"""gh issue create --repo {gh_repo} --title '{issue_title}' --body "{issue_body}" --label '{issue_labels}' --web""")
    logging.info(f"URL: {url}")
    return


def create_github_issue(gh_repo, issue_title, issue_body, issue_labels):
    """
    Creates a GitHub issue in the specified repository.

    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_title (str): The title of the issue.
        issue_body (str): The body of the issue.
        issue_labels (str): A comma-separated string of labels for the issue.

    Returns:
        str: The URL of the created issue if successful, None otherwise.
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
        return response.json()["html_url"]
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
    
    
parser = argparse.ArgumentParser(description='Generate labels for a given bookmark.')
parser.add_argument('--url', metavar='url', type=str, help='The url of the bookmark.')
parser.add_argument('--title', metavar='title', type=str, help='The title of the bookmark.')
parser.add_argument('--snippet', metavar='snippet', type=str, help='The selected text of the bookmark.')
parser.add_argument('--repo', metavar='repo', type=str, help='The repo to get labels from.', default="irthomasthomas/undecidability")
parser.add_argument('--draft', metavar='draft', type=bool, help='Create a draft issue.', default=False)

args = parser.parse_args()

# Configure logging to a file
logging.basicConfig(filename='/tmp/app.log', level=logging.INFO)

labels_json = generate_labels(args.url, args.title, args.snippet, args.repo)
picked_labels = labels_json['picked_labels']['label_names']
generated_labels = labels_json['generated_labels']

url = bookmark_to_gh_issues(args.title, args.url, args.snippet, labels_json, generated_labels, args.repo)

# os.system(f"open {url}") # sh: line 1: open: command not found
os.system(f"xdg-open {url} & disown")