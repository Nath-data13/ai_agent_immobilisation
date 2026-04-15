import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "documents.json"

def get_operation_file(file_uuid: str, operation_id: str) -> dict :
    with open(DATA_PATH, encoding="utf-8")as f:
        documents = json.load(f)

    for document in documents:
        if document["file_uuid"] == file_uuid:
            return document
    
    raise ValueError(f"Aucune document trouvée pour : {file_uuid}")

