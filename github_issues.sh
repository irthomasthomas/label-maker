#!/bin/bash

# github_issues.sh

send_note_to_github() {
    local TITLE="$1"
    local URL="$2"
    local DESCRIPTION="$3"
    local BODY
    local task_list
    local labels_csv
    local issue_url

    if [ -z "$TITLE" ]; then
        TITLE="$(llm "generate a title from this url:$URL:quote:$DESCRIPTION" -o temperature 0.1)"
    fi

    task_list="- [ ] [${TITLE}](${URL})"
    BODY="$task_list

    $DESCRIPTION"
    labels_csv=$(get_labels "$TITLE" "$URL" "$DESCRIPTION")
    # print to stderr
    echo "title: $TITLE
url: $URL 
description: $DESCRIPTION
labels: $labels_csv
" >&2
    # issue_url=$(gh issue create --title "$TITLE" --body "$BODY" --label "$labels_csv")
    # echo "$issue_url"
}


get_labels() {
    local TITLE="$1"
    local URL="$2"
    local DESCRIPTION="$3"
    local labels
    local labels_csv
    labels=$(python /home/thomas/Development/Projects/llm/ai-issues/llm_label_maker/label_maker.py --url "$URL" --title "$TITLE" --description "$DESCRIPTION")
    labels_csv=$(echo "$labels" | tr -d [])
    labels_csv=$(echo "$labels_csv" | tr -d \' | tr -d ' ')
    echo "$labels_csv"
}

# Main execution
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <title> <url> <DESCRIPTION>"
    exit 1
fi

send_note_to_github "$1" "$2" "$3"