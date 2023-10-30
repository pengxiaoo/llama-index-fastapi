import csv
import json
from app.data.models.qa import Source


def csv_to_jsonl(csv_file_path, jsonl_file_path):
    with open(csv_file_path, 'r') as csv_file, open(jsonl_file_path, 'w') as jsonl_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            ordered_row = {
                'source': Source.KNOWLEDGE_BASE.value,
                'category': row['category'],
                'question': row['question'],
                'answer': row['answer']
            }
            jsonl_file.write(json.dumps(ordered_row) + '\n')


if __name__ == "__main__":
    input_file_path = '../documents/golf-knowledge-base.csv'
    output_file_path = '../documents/golf-knowledge-base.jsonl'
    csv_to_jsonl(input_file_path, output_file_path)
