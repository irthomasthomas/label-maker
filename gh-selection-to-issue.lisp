(define-command-global gh-send-selection-to-issue ()
  "Sends URL, title, and selected text to a new GitHub issue using github_issues.py."
  (let* ((title (title (current-buffer)))
         (myurl (url (current-buffer)))
         (selection
          (ps-eval
           (parenscript:chain window (get-selection) (to-string))))
         (repo "irthomasthomas/undecidability") ;; Default repository. Change as needed.
         ;; Path to your python script
         (python-script "/home/thomas/Development/LLMs/label-maker/github_issues.py")
         ;; Construct the command to execute the Python script with arguments
         (command (format nil "python3 ~a --title '~a' --url '~a' --description '~a' --repo '~a'"
                          python-script
                          title myurl selection repo)))
    ;; Execute the command in the background
    (uiop:run-program (list "sh" "-c" command) :output t)))