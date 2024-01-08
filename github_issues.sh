#!/bin/bash

# github_issues.sh

send_note_to_github() {
    local TITLE="$1"
    local URL="$2"
    local DESCRIPTION="$3"
    local labels="$4"
    local gh_markdown_highlight_generated_labels="$5"
    local BODY
    local task_list
    local issue_url
    local labels_csv
    echo >&2
    echo "send_note_to_github" >&2
    echo "gh_markdown_highlight_generated_labels: $gh_markdown_highlight_generated_labels" >&2

    echo >&2
    if [ -z "$TITLE" ]; then
        TITLE="$(llm "generate a title from this url:$URL:quote:$DESCRIPTION" -o temperature 0.1)"
    fi
    
    task_list="- [ ] [${TITLE}](${URL})"
    suggested_labels="#### Suggested labels
#### $gh_markdown_highlight_generated_labels"
    
    BODY="$task_list

$DESCRIPTION

$suggested_labels"
    labels_csv=$(echo "$labels" | tr '\n' ',' | sed 's/.$//')
    echo "labels_csv: $labels_csv" >&2
    
    issue_url=$(gh issue create --title "$TITLE" --body "$BODY" --label "$labels_csv" --web)
    echo "$issue_url"
}


get_labels_json() {
    local TITLE="$1"
    local URL="$2"
    local DESCRIPTION="$3"
    local labels=$(python /home/thomas/Development/Projects/llm/label-maker/label_maker.py --url "$URL" --title "$TITLE" --description "$DESCRIPTION")
    echo "$labels"
}

# Main execution
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <title> <url> <DESCRIPTION>"
    exit 1
fi

TITLE="$1"
URL="$2"
DESCRIPTION="$3"

labels_json=$(get_labels_json "$TITLE" "$URL" "$DESCRIPTION")
generate_labels=$(echo "$labels_json" | jq '.generated_labels | to_entries[]')

picked_labels=$(echo "$labels_json" | jq '.picked_labels | to_entries[] | select(.value == true) | .key')
gh_markdown_highlight_generated_labels=$(echo "$generate_labels" | tr '\n' ' ' | sed 's/.$//')

send_note_to_github "$TITLE" "$URL" "$DESCRIPTION" "$picked_labels" "$gh_markdown_highlight_generated_labels"