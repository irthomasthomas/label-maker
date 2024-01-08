#!/bin/bash
# nyxt_to_github.sh

create_pipes() {
    echo "create pipes"
    if [ ! -p "$pipe_title" ]; then
        mkfifo "$pipe_title" && echo "Created named pipe: $pipe_title" >&2
    fi

    if [ ! -p "$pipe_url" ]; then
        mkfifo "$pipe_url" && echo "Created named pipe: $pipe_url" >&2
    fi

    if [ ! -p "$pipe_selection" ]; then
        mkfifo "$pipe_selection"   && echo "Created named pipe: $pipe_selection" >&2
    fi

    if [ ! -d "$target_directory" ]; then
        echo "Cannot find directory $target_directory" >&2
        exit 1
    fi
}

monitor_nyxt_to_gh_pipes() {
    local TITLE
    local URL
    local SELECTION
    local issue_url
    echo "monitoring pipes" >&2

    TITLE="$(cat ${pipe_title})"
    URL="$(cat $pipe_url)"
    SELECTION="$(cat $pipe_selection)"

    echo "TITLE: $TITLE\nURL: $URL\n SELECTION: $SELECTION\n" >&2
    /home/thomas/Development/Projects/llm/label-maker/github_issues.sh "$TITLE" "$URL" "$SELECTION"
}

target_project="undecidability"
target_directory="$HOME/$target_project"
cd "$target_directory" || return 2
echo "$PWD"

pipe_title="/tmp/nyxt_title"
pipe_url="/tmp/nyxt_url"
pipe_selection="/tmp/nyxt_selection"


# Main loop
echo "Starting nyxt-to-gh.sh"
while true; do
    create_pipes
    monitor_nyxt_to_gh_pipes
    sleep 5
done