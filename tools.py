tools = [
        {
            "type": "function",
            "function": {
                "name": "create_new_label",
                "description": "Create a new label for the bookmark.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "The GitHub repository to create a label for."},
                        "name": {
                            "type": "string",
                            "description": "The name of the label."},
                        "description": {
                            "type": "string",
                            "description": "The description of the label."},
                    },
                    "required": ["repo", "name", "description"],
                },
            }
        }
    ]


tools = [ # WARNING: DO NOT REMOVE THE TOOL CALLS, EVEN IF YOU ARE NOT USING THEM. THE MODEL WILL NOT WORK WITHOUT THEM.
            {
            "type": "function",
            "function": {
                "name": "request_labels_list",
                "description": "Request a list of labels from the repo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "The GitHub repository to request labels for."},
                        },
                    "required": ["repo"],
                    },
                }
            },
            {
            "type": "function",
            "function": {
                "name": "pick_labels",
                "description": "Save a list of gh issue labels for the request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "labels": {
                            "type": "string",
                            "description": "A list of labels."},
                        "url": {
                            "type": "string",
                            "description": "The url of the bookmark."},
                        "title": {
                            "type": "string",
                            "description": "The title of the bookmark."},
                        "description": {
                            "type": "string",
                            "description": "The selected text of the bookmark."},
                    },
                    "required": ["labels", "url", "title", "description"],
                },
            }
            },
        ]

