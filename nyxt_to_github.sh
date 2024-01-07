#!/bin/bash

# nyxt_to_github.sh

target_project="undecidability"
target_directory="$HOME/$target_project"
cd "$target_directory" || return 2
echo "$PWD"

pipe_title="/tmp/nyxt_title"
pipe_url="/tmp/nyxt_url"
pipe_selection="/tmp/nyxt_selection"

create_pipes() {
    echo "create pipes"
    if [ ! -p "$pipe_title" ]; then
        mkfifo "$pipe_title" && echo "Created named pipe: $pipe_title"
    fi

    if [ ! -p "$pipe_url" ]; then
        mkfifo "$pipe_url" && echo "Created named pipe: $pipe_url"
    fi

    if [ ! -p "$pipe_selection" ]; then
        mkfifo "$pipe_selection"   && echo "Created named pipe: $pipe_selection"
    fi

    if [ ! -d "$target_directory" ]; then
        echo "Cannot find directory $target_directory"
        exit 1
    fi
}

monitor_nyxt_to_gh_pipes() {
    local TITLE
    local URL
    local SELECTION
    local issue_url

    TITLE="$(cat ${pipe_title})"
    URL="$(cat $pipe_url)"
    SELECTION="$(cat $pipe_selection)"
    # echo "TITLE: $TITLE\nURL: $URL\n SELECTION: $SELECTION\n"
    sh /home/thomas/Development/Projects/llm/ai-issues/github_issues.sh "$TITLE" "$URL" "$SELECTION"
    # issue_url=$(/home/thomas/Development/Projects/llm/ai-issues/github_issues.sh "$TITLE" "$URL" "$SELECTION")
    # echo "issue_url: $issue_url"
    # nyxt "$issue_url"
}

# Main loop
echo "Starting nyxt-to-gh.sh"
while true; do
    create_pipes
    monitor_nyxt_to_gh_pipes
    sleep 5
done