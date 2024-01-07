def bulk_label_maker():
    try:
        conn = sqlite3.connect("logs.db")
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS labels (responses_id TEXT PRIMARY KEY REFERENCES [responses]([id]), prompt TEXT, labels TEXT);")

        cur.execute("SELECT id, prompt FROM responses;")
        data = cur.fetchall()

        for i, row in enumerate(data, start=1):
            id, prompt = row
            truncated_prompt = prompt[:400]  # Truncate prompt to 400 characters
            print(f"Truncated Prompt: {truncated_prompt}")

            labels = generate_labels(truncated_prompt)
            print(labels)

            if i > 1000:
                break

        conn.commit()
        print("All data committed to the database.")
    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()

