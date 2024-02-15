(define-command-global gh-send-selection-to-issue ()
  "Sends URL, title, and selected text to a new GitHub issue using github_issues.py."
  (let* ((title (title (current-buffer)))
         (myurl (quri:render-uri (url (current-buffer))))
         (selection
          (ps-eval
           (parenscript:chain window (get-selection) (to-string))))
         (repo "irthomasthomas/undecidability") 
         (python-script "/home/thomas/Development/LLMs/label-maker/github_issues.py")
         (python-interpreter "/home/thomas/Development/Projects/llm/.venv/bin/python3")
         ;; Construct the command to execute the Python script with arguments
         (command (list python-interpreter python-script "--title" title "--url" myurl "--snippet" selection "--repo" repo)))
    ;; Execute the command in the background
    (uiop:run-program command :output t)))