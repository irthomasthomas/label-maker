Here's the merged final document:

# GitHub Issues AI Assistant

This repository contains a collection of Python scripts and a Nyxt browser plugin that form an AI-powered assistant for managing GitHub issues. The main functionalities include:

1. **Automatic Label Generation**: The `label_maker.py` script uses Jina-embedding-v2-base to generate embeddings for issue content and intelligently generate labels based on the issue title, body, and URL. It can create new labels if the existing ones are inadequate to properly categorize the issue.

2. **Duplicate Issue Detection**: The `github_issues.py` script employs vector embeddings to find similar issues in the repository. It calculates the cosine similarity between the embeddings of the new issue and existing issues to detect potential duplicates.

3. **Related Issue Linking**: When creating a new issue, the assistant searches for related issues and includes links to them in the issue body. This helps to maintain a well-connected issue tracker.

4. **Issue Creation from Web Pages**: The `nyxt-browser-plugin.lisp` file provides a browser plugin for the Nyxt browser that allows users to create GitHub issues directly from web pages. The plugin sends the page URL, title, and selected text to the `github_issues.py` script for processing.

5. **Issue Management**: The scripts provide functions to create, update, comment on, and view GitHub issues. This allows for easy management and collaboration on issues.

6. **Database Integration**: The repository uses SQLite databases to store issue embeddings and metadata. This allows for efficient similarity searches and data persistence.

## Example Usage: Turning GitHub Issues into a Knowledge Base and Webring

One powerful use case for the GitHub Issues AI Assistant is to create a personal knowledge base and webring using GitHub issues. Here's how it works:

1. When you come across an interesting web page, use the `send-snippet-to-gh-issue` command from the Nyxt browser plugin to create a new GitHub issue. The assistant will automatically generate relevant labels and detect any similar issues in your repository.

2. If there are related issues, the assistant will include links to them in the new issue's body. This allows you to easily navigate between connected pieces of information.

3. Other users can also reference your issues in their own repositories. When they do so, those references will appear in your original issue, creating a webring effect. This enables organic discovery and sharing of knowledge across multiple repositories.

By leveraging the AI-powered features of the assistant, you can effortlessly build a rich, interconnected knowledge base using GitHub issues. The automatic labeling and duplicate detection ensure that your information remains organized and easy to navigate. The ability to link related issues within and across repositories creates a powerful webring that facilitates collaboration and knowledge sharing.


## Imaginative Use Cases

This project can be used for various purposes:

1. **Personal Knowledge Management**: Use the issue creation and labeling capabilities to organize and categorize your bookmarks, notes, and ideas. The similarity matching can help you discover related content and make connections between different pieces of information.

2. **Research and Literature Review**: Create GitHub issues for each paper, article, or resource you come across. The labeling and similarity features can help you group related papers, identify key themes, and find relevant references.

3. **Project Management**: Utilize the issue creation and management functionalities to track tasks, bugs, and feature requests for your projects. The labeling system can help you prioritize and categorize issues based on their type, urgency, or complexity.

4. **Collaborative Brainstorming**: Engage in collaborative brainstorming sessions by creating GitHub issues for each idea or topic. The similarity matching can help you find related ideas, spark new thoughts, and foster creative discussions among team members.

5. **Content Curation**: Use the project to curate and organize content from various sources. Create issues for interesting articles, videos, or resources you find, and use the labeling and similarity features to build a structured collection of curated content.

## Future Development

Here are a few ideas for future development of the project:

1. **Label Refinement**: Improve the label generation process by fine-tuning the embeddings model on a dataset of well-labeled GitHub issues.

2. **Issue Prioritization**: Develop an AI-based system to automatically prioritize issues based on factors such as urgency, impact, and complexity.

3. **Cross-Repository Issue Linking**: Extend the related issue linking feature to work across multiple repositories, allowing for better collaboration and knowledge sharing.

4. **Enhanced Similarity Matching**: Explore more advanced techniques for measuring similarity between issues, such as using different embedding models or incorporating additional metadata.

5. **User Interface**: Develop a user-friendly web interface or command-line tool to interact with the project, making it easier for users to create issues, manage labels, and explore similar content.

6. **Integration with Other Platforms**: Extend the functionality to support other platforms beyond GitHub, such as Gitlab, Jira, or Trello, to provide a unified issue management experience across different tools.

With its powerful AI capabilities and seamless integration with GitHub and web browsers, the GitHub Issues AI Assistant has the potential to revolutionize issue management and boost productivity for development teams and knowledge workers alike.
