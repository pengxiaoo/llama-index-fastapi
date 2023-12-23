import csv
from app.data.models.qa import Source, Answer


def load_standard_answers_from_csv(csv_file_path) -> list[Answer]:
    with open(csv_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        standard_answers = []
        for row in reader:
            answer = Answer(
                category=row["category"],
                question=row["question"],
                answer=row["answer"],
                source=Source.KNOWLEDGE_BASE,
            )
            standard_answers.append(answer)
        return standard_answers
