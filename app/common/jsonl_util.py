import csv
import json

input_file_path = '../documents/golf-knowledge-base.csv'
output_file_path = '../documents/golf-knowledge-base.jsonl'


def build_jsonl_from_csv():
    with open(input_file_path, 'r') as csv_file, open(output_file_path, 'w') as jsonl_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            ordered_row = {
                'source': 'gpt3.5',
                'category': row['category'],
                'question': row['question'],
                'answer': row['answer']
            }
            jsonl_file.write(json.dumps(ordered_row) + '\n')


if __name__ == "__main__":
    build_jsonl_from_csv()
