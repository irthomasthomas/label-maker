# github\_issues.py and label\_maker.py: A Code Repository for Automating GitHub Issue Management

This repository contains two Python scripts, `github_issues.py` and `label_maker.py`, that can be used together to automate the process of creating and managing GitHub issues. These scripts use the GitHub API and OpenAI's GPT-3 language model to generate labels, summarize issue descriptions, and check for duplicate issues.

## Features

- Automatically generate labels for issues based on the issue content
- Summarize issue descriptions for clarity and brevity
- Check for duplicate issues based on content similarity
- Create and manage GitHub issues using the GitHub API
- Utilize OpenAI's GPT-3 for natural language processing tasks

## Usage

1. **Setup**:

   - Ensure you have Python 3.x installed
   - Clone this repository
   - Create a virtual environment and install the required packages:

     ```
     $ python3 -m venv .venv
     $ source .venv/bin/activate
     $ pip install -r requirements.txt
     ```

2. **Configuration**:

   - Set the `OPENAI_API_KEY` and `GITHUB_TOKEN` environment variables

3. **Running the scripts**:

   - Run `label_maker.py` with the required arguments:

     ```
     $ python3 label_maker.py --url <url> --title <title> --snippet <snippet> --repo <repo>
     ```

   - Run `github_issues.py` to handle the GitHub API requests

## Future Development

- [ ] Implement a command-line interface for easier use
- [ ] Add support for more features, such as issue commenting and merging
- [ ] Improve the label generation algorithm with more sophisticated NLP techniques

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
