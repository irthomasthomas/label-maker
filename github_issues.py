#!/usr/bin/env python3
import subprocess
import requests
import json
import webbrowser

def send_note_to_github(title, url, description, labels, gh_markdown_highlight_generated_labels, repo):
    if not title:
        # Simulating external CLI tool for title generation, replace 'llm' command with actual API call or logic if needed.
        title = "Generated Title based on URL and Description"  # Placeholder logic

    print("Generating description")
    # Description generation logic (Placeholder)
    description = "Beautiful Markdown Generated Description"  # Replace with actual markdown generation logic
    print("Done generating description")

    task_list = f"- [ ] [{title}]({url})"
    suggested_labels = f"#### Suggested labels\n#### {gh_markdown_highlight_generated_labels}"

    body = f"{task_list}\n\n{description}\n\n{suggested_labels}"
    print(f"github_issues > send_note_to_github: labels:\n{labels}")

    labels_csv = '","'.join(labels.replace(" ", "").split("\n"))
    
    issue_url = create_github_issue(repo, title, body, labels_csv)
    webbrowser.open(issue_url)
    focus_browser_window()

def create_github_issue(repo, title, body, labels):
    command = ['gh', 'issue', 'create', '-R', repo, '--title', title, '--body', body, '--label', labels]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip()

def focus_browser_window():
    subprocess.run(['wmctrl', '-a', 'Nyxt'])

def get_labels_json(title, url, description):
    # Placeholder for label generation, replace with actual external call or logic.
    labels_json = {"generated_labels": ["bug", "feature"], "picked_labels": {"label_names": ["improvement", "urgent"]}}
    return labels_json

def main(title, url, description, repo="irthomasthomas/undecidability"):
    print("TITLE:", title)
    print("URL:", url)

    labels_json = get_labels_json(title, url, description)
    generate_labels = ' '.join(labels_json.get("generated_labels", []))
    picked_labels = '\n'.join(labels_json.get("picked_labels", {}).get("label_names", []))

    gh_markdown_highlight_generated_labels = generate_labels.rstrip(',')
    send_note_to_github(title, url, description, picked_labels, gh_markdown_highlight_generated_labels, repo)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: <script> <title> <url> <description>")
        sys.exit(1)

    title = sys.argv[1]
    url = sys.argv[2]
    description = sys.argv[3]
    main(title, url, description)