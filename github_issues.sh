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
    echo "FUNC: github_issues.sh > send_note_to_github" >&2
    echo "generated_labels: $gh_markdown_highlight_generated_labels" >&2

    echo >&2
    if [ -z "$TITLE" ]; then
        TITLE="$(llm "generate a title from this url:$URL:quote:$DESCRIPTION" -o temperature 0.1)"
    fi
    DESCRIPTION=$(llm -m mistral-small "Reformat this into a beautiful github issues markdown: $DESCRIPTION" -o temperature 1)
    
    task_list="- [ ] [${TITLE}](${URL})"
    suggested_labels="#### Suggested labels
#### $gh_markdown_highlight_generated_labels"
    
    BODY="$task_list

$DESCRIPTION

$suggested_labels"
    labels_csv=$(echo "$labels" | tr '\n' ',' | sed 's/.$//')
    echo "TITLE: $TITLE" >&2
    echo "BODY: $BODY" >&2
    issue_url=$(gh issue create --title "$TITLE" --body "$BODY" --label "$labels_csv")
    nyxt "$issue_url"
    WIN_ID=$(wmctrl -l | grep "^.*Nyxt - " | awk '{print $1}')
    wmctrl -i -a "$WIN_ID"

}


get_labels_json() {
    echo >&2
    
    echo "FUNC: github_issues.sh > get_labels_json" >&2
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
echo >&2
echo >&2
TITLE="$1"
URL="$2"
DESCRIPTION="$3"
echo "TITLE: $TITLE" >&2
echo "URL: $URL" >&2
# echo "DESCRIPTION: $DESCRIPTION" >&2
echo >&2
labels_json=$(get_labels_json "$TITLE" "$URL" "$DESCRIPTION")
echo "labels_json: $labels_json" >&2
echo >&2
generate_labels=$(echo "$labels_json" | jq '.new_labels_created | to_entries[]')
# echo "generate_labels: $generate_labels" >&2
echo >&2
picked_labels=$(echo "$labels_json" | jq '.existing_labels_picked | to_entries[] | select(.value == true) | .key')
# echo "picked_labels: $picked_labels" >&2
gh_markdown_highlight_generated_labels=$(echo "$generate_labels" | tr '\n' ' ' | sed 's/.$//')
# echo "gh_markdown_highlight_generated_labels: $gh_markdown_highlight_generated_labels" >&2

send_note_to_github "$TITLE" "$URL" "$DESCRIPTION" "$picked_labels" "$gh_markdown_highlight_generated_labels"