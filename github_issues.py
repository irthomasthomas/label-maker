import llm
import os
import argparse
import logging

from label_maker import gh_api_request, generate_labels


def send_note_to_github(title, url, description, labels, gh_markdown_highlight_generated_labels, repo):
    model = llm.get_model("gpt-3.5-turbo")
    model.key = os.getenv("OPENAI_API_KEY")
    if not title:
        title = model.prompt(f"generate a title from this url:{url}:quote:{description}", temperature=0.1).text()

    # Reformat description
    description_prompt = f"Reformat this into beautiful markdown(GFM). Keep the wording exact. Only edit formatting. Include the entire content. **IMPORTANT** ADD NO ADDITIONAL COMMENTARY OR TEXT OF ANY KIND.\n**CONTENT**:\n'''TITLE:{title}\nDESCRIPTION:{description}\nURL:{url}'''"
    description = model.prompt(description_prompt, temperature=0.1).text()

    task_list = f"- [ ] [{title}]({url})"
    suggested_labels = f"#### Suggested labels\n#### {gh_markdown_highlight_generated_labels}"

    body = f"{task_list}\n\n{description}\n\n{suggested_labels}"
    picked_labels = labels['picked_labels']['label_names']

    issue_url = create_github_issue(repo, title, body, picked_labels)
    print(f"Issue created: {issue_url}")


def create_github_issue(repo, title, body, labels):
    """
    Creates a GitHub issue.
    
    :param repo: Repository name including the owner (e.g., "owner/repo")
    :param title: Issue title
    :param body: Issue body description
    :param labels: Comma-separated string of labels
    :return: URL of the created issue or None
    """
    print(f"labels: {labels}")
    data = {
        "title": title,
        "body": body,
        "labels": labels.split(",")
    }
    print(f"data: {data}")
    
    response = gh_api_request(repo, method="POST", endpoint="/issues", data=data)
    if response.ok:
        return response.json()["html_url"]
    else:
        print(f"Failed to create issue: {response.text}")
        return None
    

parser = argparse.ArgumentParser(description='Generate labels for a given bookmark.')
parser.add_argument('--url', metavar='url', type=str, help='The url of the bookmark.')
parser.add_argument('--title', metavar='title', type=str, help='The title of the bookmark.')
parser.add_argument('--description', metavar='description', type=str, help='The selected text of the bookmark.')
parser.add_argument('--repo', metavar='repo', type=str, help='The repo to get labels from.', default="irthomasthomas/undecidability")

args = parser.parse_args()
logging.basicConfig(level=logging.INFO)

labels_json = generate_labels(args.url, args.title, args.description, args.repo)
picked_labels = labels_json['picked_labels']['label_names']
generated_labels = labels_json['generated_labels']

url = send_note_to_github(args.title, args.url, args.description, labels_json, generated_labels, args.repo)

os.system(f"open {url}")