#!/bin/sh
# nyxt_to_github.sh

create_pipes() {
    # Todo. I think there is problem when nyxt creates the files before this script is launched. They will not be fifo files.
    echo >&2
    echo "FUNC: nyxt_to_github.sh > create pipes"
    if [ ! -p "$pipe_title" ]; then # Problem.
        mkfifo "$pipe_title" && echo "Created named pipe: $pipe_title" >&2
    fi

    if [ ! -p "$pipe_url" ]; then
        mkfifo "$pipe_url" && echo "Created named pipe: $pipe_url" >&2
    fi

    if [ ! -p "$pipe_selection" ]; then
        mkfifo "$pipe_selection"   && echo "Created named pipe: $pipe_selection" >&2
    fi

}

monitor_nyxt_to_gh_pipes() {
    local TITLE
    local URL
    local SELECTION
    local issue_url
    echo >&2
    echo "FUNC: nyxt_to_github.sh > monitor_nyxt_to_gh_pipes" >&2

    TITLE="$(cat ${pipe_title})"
    URL="$(cat $pipe_url)"
    SELECTION="$(cat $pipe_selection)"

    #short_selection="$(echo "$SELECTION" | cut -c 1-100)"
    /home/thomas/Development/Projects/llm/label-maker/github_issues.sh "$TITLE" "$URL" "$SELECTION"
}


pipe_title="/tmp/nyxt_title"
pipe_url="/tmp/nyxt_url"
pipe_selection="/tmp/nyxt_selection"


# Main loop
echo >&2
while true; do
    create_pipes
    monitor_nyxt_to_gh_pipes
    sleep 5
done