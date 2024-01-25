#!/bin/zsh

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
    
    if [ -z "$TITLE" ]; then
        TITLE="$(llm "generate a title from this url:$URL:quote:$DESCRIPTION" -o temperature 0.1)"
    fi
    echo "Generating description" >&2
    DESCRIPTION=$(llm -m mistral-small "Reformat this into beautiful markdown. DO NOT rewrite it or editorialize it in any way: $DESCRIPTION" -o temperature 1)
    echo "Done generating description" >&2
    task_list="- [ ] [${TITLE}](${URL})"
    suggested_labels="#### Suggested labels
#### $gh_markdown_highlight_generated_labels"
    
    BODY="$task_list

$DESCRIPTION

$suggested_labels"
    labels_csv=$(echo "$labels" | tr "\n" "," | sed "s/.$//" | sed "s/,/\",\"/g")
    # remove spaces
    labels_csv=$(echo "$labels_csv" | sed "s/ //g")
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
echo "$labels_json" >&2
generate_labels=$(echo "$labels_json" | jq '.generated_labels')
picked_labels=$(echo "$labels_json" | jq '.picked_labels .label_name')

gh_markdown_highlight_generated_labels=$(echo "$generate_labels" | tr '\n' ' ' | sed 's/.$//')
send_note_to_github "$TITLE" "$URL" "$DESCRIPTION" "$picked_labels" "$gh_markdown_highlight_generated_labels"