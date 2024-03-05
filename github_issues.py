import json
from math import exp
import shlex
import sqlite3
import subprocess
import time
import llm
import os
import argparse
import logging
import sqlite_utils
from label_maker import gh_api_request, generate_labels
from openai import OpenAI
from typing import Any, Optional, Dict, Union, List, Tuple

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
)


def logprobs_duplicate_check(title: str, issue_body: str, result_title: str, result_body: str, related: Any) -> None:
    """
    Checks if two sets of titles and bodies are likely duplicates using OpenAI's GPT-3.5 Turbo model.

    Args:
        title (str): The title of the first set.
        issue_body (str): The body of the first set.
        result_title (str): The title of the second set.
        result_body (str): The body of the second set.
        related (Any): The related score between the two sets.

    Returns:
        None
    """
    
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
                    
        cosine similarity: {related.score}
                    
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
        logging.info(f"{logprob.token}: {round(exp(logprob.logprob)*100,2)}%")


def format_md_hidden_note(note, title="Expand for details"):
    """
    Formats the hidden note for GitHub issues.

    Args:
        note (str): The note to format.

    Returns:
        str: The formatted note.
    """
    return f"<details>\n<summary>{title}</summary>\n\n{note}\n\n</details>"


def bookmark_to_gh_issues(page_title: str, labels: Dict[str, Any], repo: str, body: str, draft: bool = False) -> Optional[Dict[str, Any]]:
    """
    Creates a GitHub issue based on the provided parameters.

    Args:
        page_title (str): The title of the page.
        labels (Dict[str, Any]): A dictionary containing the labels for the issue.
        repo (str): The name of the repository where the issue will be created.
        body (str): The body content of the issue.
        draft (bool, optional): Specifies whether the issue should be created as a draft. Defaults to False.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representing the created issue, or None if the issue creation failed.
    """

    picked_labels = labels['picked_labels']['label_names']
    issue_json = False
    if draft:
        gh_create_draft_issue(repo, page_title, body, picked_labels)
    else:
        issue_json = gh_create_issue(repo, page_title, body, picked_labels)
        logging.info(f"Issue created: {issue_json}")
    return issue_json


def gh_format_issue(page_title: str, page_url: str, page_snippet: str, new_label_note: str = ""):  
    """
    Formats the issue content for GitHub issues.

    Args:
        page_title (str): The title of the page.
        page_url (str): The URL of the page.
        page_snippet (str): The snippet of the page content.
        new_label_note (str, optional): Additional note for new labels. Defaults to "".

    Returns:
        tuple: A tuple containing the formatted page title and body.
    """
    
    model = llm.get_model("gpt-3.5-turbo")
    model.key = os.getenv("OPENAI_API_KEY")
    if not page_title:
        page_title = model.prompt(f"generate a title from this url:{page_url}:quote:{page_snippet}", temperature=0.4).text()

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


def gh_create_draft_issue(gh_repo: str, issue_title: str, issue_body: str, issue_labels: str) -> None:
    """
    Creates a draft issue on GitHub using the provided repository, title, body, and labels.

    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_title (str): The title of the issue.
        issue_body (str): The body of the issue.
        issue_labels (str): The labels to be assigned to the issue.

    Returns:
        None
    """
    issue_body = shlex.quote(issue_body)
    issue_title = shlex.quote(issue_title)
    issue_labels = shlex.quote(issue_labels)
    
    command = f"gh issue create --repo {gh_repo} --title {issue_title} --body {issue_body} --label {issue_labels} --web"
    
    subprocess.run(shlex.split(command))
    
    return


def gh_view_issue(issue_number: int, web: bool = False, pretty_print: bool = False) -> Tuple[str, str]:
    """
    View a GitHub issue.

    Args:
        issue_number (int): The number of the issue to view.
        web (bool, optional): Whether to open the issue in a web browser. Defaults to False.
        pretty_print (bool, optional): Whether to pretty print the output. Defaults to False.

    Returns:
        Tuple[str, str]: A tuple containing the title and body of the issue.
    """
    
    logging.info("gh_view_issue")
    logging.info(f"issue_number: {issue_number}")
    logging.info(f"web: {web}")
    logging.info(f"pretty_print: {pretty_print}")
    
    if pretty_print:
        subprocess.run(shlex.split(command)) # pretty print gh output
    elif web:
        command = f"gh issue view {issue_number} -R 'irthomasthomas/undecidability' --web"
        logging.info(f"command: {command}")
        subprocess.run(shlex.split(command))
    else:
        command = f"gh issue view {issue_number} -R 'irthomasthomas/undecidability' --json body,title"
        logging.info(f"command: {command}")
        response = subprocess.run(shlex.split(command), capture_output=True)
        
        response_json = json.loads(response.stdout.decode())
        body = response_json["body"]
        title = response_json["title"]
        
        return (title, body)
    
    
def gh_create_issue(gh_repo: str, issue_title: str, issue_body: str, issue_labels: str) -> Optional[Dict[str, Any]]:
    """
    Create a new issue in a GitHub repository.

    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_title (str): The title of the issue.
        issue_body (str): The body of the issue.
        issue_labels (str): A comma-separated string of labels for the issue.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representing the created issue if successful, None otherwise.
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
    

def gh_get_all_issues(gh_repo: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches all issues from a GitHub repository.

    Args:
        gh_repo (str): The name of the GitHub repository.

    Returns:
        Optional[List[Dict[str, Any]]]: A list of dictionaries representing the issues,
        or None if the request fails.
    """
    logging.info(f"gh_get_all_issues: gh_repo: {gh_repo} ")
    response = gh_api_request(gh_repo, method="GET", endpoint="/issues")
    if response.ok:
        return response.json()
    else:
        logging.error(f"Failed to fetch issues: {response.text}")
        return None
    

def gh_issue_update(gh_repo: str, issue_number: int, issue_title: str = "", issue_body: str = "", issue_labels: str = ""):
    """
    Update an issue in a GitHub repository.

    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_number (int): The number of the issue to update.
        issue_title (str, optional): The new title for the issue. Defaults to "".
        issue_body (str, optional): The new body for the issue. Defaults to "".
        issue_labels (str, optional): The new labels for the issue, separated by commas. Defaults to "".

    Returns:
        bool: True if the issue was successfully updated, False otherwise.
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
       

def gh_add_issue_comment(gh_repo: str, issue_number: int, comment: str):
    """
    Add a comment to a GitHub issue.
    
    Args:
        gh_repo (str): The name of the GitHub repository.
        issue_number (int): The number of the issue to add the comment to.
        comment (str): The comment to add.
        
    Returns:
        bool: True if the comment was successfully added, False otherwise.
    """
        
    data = {
        "body": comment
    }
    response = gh_api_request(gh_repo, method="POST", endpoint=f"/issues/{issue_number}/comments", data=data)
    if not response.ok:
        logging.error(f"Failed to add comment to issue: {response.text}")
    return response.ok


def create_embedding_vector(title: str, issue_body: str, issue_number: int, database: str, collection: str) -> None:
    """
    Creates an embedding vector for a given title and issue body, and stores it in a database collection.

    Args:
        title (str): The title of the issue.
        issue_body (str): The body of the issue.
        issue_number (int): The number of the issue.
        database (str): The path to the SQLite database file.
        collection (str): The name of the collection in the database.

    Returns:
        None
    """
    
    db = sqlite_utils.Database(database)
    collection_obj = llm.Collection(collection, db, create=True)
    content = f"{title} {issue_body}"
    collection_obj.embed(str(issue_number), content, store=True, metadata={"title": title, "issue_body": issue_body, "issue_number": issue_number})
    return issue_number


def save_gh_issue_to_db(issue_id: int, gh_issues_db: str) -> None:
    """
    Saves a GitHub issue to a SQLite database.

    Args:
        issue_id (int): The ID of the GitHub issue to save.
        gh_issues_db (str): The path to the SQLite database file.

    Returns:
        None
    """
    try:
        with sqlite3.connect(":memory:") as conn:
            conn.enable_load_extension(True)
            conn.load_extension("/home/thomas/steampipe/steampipe_sqlite_github.so")
            conn.executescript(f"""
                ATTACH DATABASE "{gh_issues_db}" AS db2;
            """)

            cursor = conn.cursor()
            with open("/home/thomas/GITHUB_TOKEN", 'r') as f:
                token = f.read()
                token_json = json.dumps({"token": token})
            query = """
                INSERT INTO db2.github_issues
                    (number, title, body, body_url, author_login, created_at, updated_at, labels_src, labels)
                SELECT number, title, body, body_url, author_login, created_at, updated_at, labels_src, labels
                FROM github_issue
                WHERE repository_full_name = ? AND number = ?;
            """
            cursor.execute(query, ('irthomasthomas/undecidability', issue_id))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error occurred in insert_github_issue: {e}")
    
    
def store_embedding_vectors_for_existing_issues(database: str, collection: str, gh_issues: list) -> None:
    """
    Store embedding vectors for existing GitHub issues in a database collection.
    
    Args:
        database (str): The path to the SQLite database file.
        collection (str): The name of the collection in the database.
        gh_issues (list): A list of GitHub issues.
    
    Returns:
        None
    """
    
    db = sqlite_utils.Database(database)
    collection_obj = llm.Collection(collection, db, create=False)
    content = [(str(issue["number"]), f"{issue['title']} {issue['body']}", {"issue": issue}) for issue in gh_issues]
    collection_obj.embed_multi_with_metadata(content, store=True)


def gh_find_similar_issues(title: str, issue_body: str, gh_issues_db: str, collection: str, related_threshold: float = 0.80) -> Tuple[List, Any]:
    """
    Finds similar issues in a given database collection based on the title and issue body.

    Args:
        title (str): The title of the issue.
        issue_body (str): The body of the issue.
        gh_issues_db (str): The path to the SQLite database file containing the GitHub issues.
        collection (str): The name of the collection in the database.
        related_threshold (float, optional): The threshold score for considering issues as related. Defaults to 0.80.

    Returns:
        Tuple[List[llm.Result], Any]: A tuple containing a list of filtered results and the embedding of the input content.
    """
    logging.info(f"gh_find_similar_issues: gh_issues_db: {gh_issues_db} collection: {collection}")
    try:
        db = sqlite_utils.Database(gh_issues_db)
        embedding_model = llm.get_embedding_model("jina-embeddings-v2-base-en")
        collection_obj = llm.Collection(collection, db, create=False)
        content = f"{title} {issue_body}"
        
        embedding = embedding_model.embed(content)

        results = collection_obj.similar_by_vector(embedding, 6)
        
        filtered_results = [entry for entry in results if entry.score > related_threshold]
    except Exception as e:
        logging.error(f"Error occurred in gh_find_similar_issues: {e}")
        return [], None
    
    return filtered_results, embedding


def generate_embedding_for_gh_issues(gh_repo, database):
    """Generates an embedding for GitHub issues."""
    
    return None


def store_embedding(
    database: str,
    id: str,
    collection_name: str,
    value: Union[str, bytes],
    metadata: Optional[Dict[str, Any]] = None,
    store: bool = False,
    embedding = None,
) -> None:
    """
    Store an embedding in the specified database.

    Args:
        database (str): The path to the SQLite database file.
        id (str): The ID of the embedding.
        collection_name (str): The name of the collection.
        value (Union[str, bytes]): The value to be stored as the embedding content.
        metadata (Optional[Dict[str, Any]], optional): Additional metadata associated with the embedding. Defaults to None.
        store (bool, optional): Whether to store the value as content in the database. Defaults to False.
        embedding (Any, optional): The embedding to be stored. Defaults to None.

    Returns:
        None: This function does not return anything.
    """
    
    db = sqlite_utils.Database(database)

    collection_obj = llm.Collection(collection_name, db, create=False)
    content_hash = collection_obj.content_hash(value)
    if db["embeddings"].count_where(
        "content_hash = ? and collection_id = ?", [content_hash, id]
    ):
        return
    
    db["embeddings"].insert(
        {
            "collection_id": collection_obj.id,
            "id": id,
            "embedding": llm.encode(embedding),
            "content": value if (store and isinstance(value, str)) else None,
            "content_blob": value if (store and isinstance(value, bytes)) else None,
            "content_hash": content_hash,
            "metadata": json.dumps(metadata) if metadata else None,
            "updated": int(time.time()),
        },
        replace=True,
    )
    return None


def issue_exists(issue_number, repository_full_name):
    """Check if a GitHub issue exists using github api."""
    
    response = gh_api_request(repository_full_name, method="GET", endpoint=f"/issues/{issue_number}")
    return response.ok


def main(args: argparse.Namespace):
    logging.basicConfig(filename='/tmp/ai_gh_issues.log', level=logging.INFO)
    logging.info(f"args:\n{args}")
    
    labels_json = generate_labels(args.url, args.title, args.snippet, args.repo)

    try:
        generated_labels = labels_json['generated_labels']
    except KeyError:
        generated_labels = ""
    logging.info(f"generated_labels: {generated_labels}")
    page_title, body = gh_format_issue(args.title, args.url, args.snippet, generated_labels)
    
    related_issues, embedding = gh_find_similar_issues(page_title, body, args.embedding_db, args.collection)
    logging.info(f"related_issues: {len(related_issues)}")
    related_threshold = 0.80
    dup_threshold = 0.94
    duplicate=False
    if related_issues:
        related_issues_md = "### Related content\n"
        for related in related_issues:
            if related.score > dup_threshold:
                duplicate = True            
                logging.info(f"Duplicate issue found: {related.id}")
                if issue_exists(related.id, args.repo):
                    gh_view_issue(related.id, web=True)
                else:
                    logging.error(f"Related issue # {related.id} found in local db does not exist in remote.")
            elif issue_exists(related.id, args.repo) and related.score > related_threshold:
                entry_title, entry_body = gh_view_issue(related.id)
                related_issues_md += f"""### #{related.id}: {entry_title}
<details><summary>### Details</summary>Similarity score: {round(related.score, 2)}\n{entry_body}</details>\n
"""
            else:
                logging.error(f"Related issue # {related.id} found in local db does not exist in remote.")

    if not duplicate:
        issue = bookmark_to_gh_issues(page_title, labels_json, args.repo, body, args.draft)
        logging.info(f"issue: {issue}")
        if issue:
            url = issue['html_url']
            id = issue['number']
            os.system(f"nyxt {url}")
            save_gh_issue_to_db(id, args.embedding_db)
            store_embedding(args.embedding_db, id, "gh-issues", f"{page_title} {body}", {"title": page_title, "body": body}, True, embedding)
            if related_issues:    
                gh_add_issue_comment(args.repo, id, related_issues_md)
    
    

parser = argparse.ArgumentParser(description='Generate labels for a given bookmark.')
parser.add_argument('--url', metavar='url', type=str, help='The url of the bookmark.')
parser.add_argument('--title', metavar='title', type=str, help='The title of the bookmark.')
parser.add_argument('--snippet', metavar='snippet', type=str, help='The selected text of the bookmark.')
parser.add_argument('--repo', metavar='repo', type=str, help='The repo to get labels from.', default="irthomasthomas/undecidability")
parser.add_argument('--draft', metavar='draft', type=bool, help='Create a draft issue.', default=False)
parser.add_argument('--embedding_db', metavar='embedding_db', type=str, help='The database to store embeddings.', default="github-issues.db")
parser.add_argument('--collection', metavar='collection', type=str, help='The collection to store embeddings.', default="gh-issues")

args = parser.parse_args()

if __name__ == "__main__":
    main(args=args)