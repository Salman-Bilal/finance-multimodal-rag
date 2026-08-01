# check_qdrant.py — developer utility to inspect stored vector payloads
from services.embedder import qdrant_client, COLLECTION_NAME


def verify_qdrant_payloads():
    records, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        limit=5,
        with_payload=True,
        with_vectors=False
    )

    if not records:
        print("❌ No vector points found in Qdrant collection!")
        return

    print(f"✅ Found {len(records)} points in collection '{COLLECTION_NAME}':\n")
    for idx, point in enumerate(records, start=1):
        payload = point.payload
        print(f"--- Point {idx} (ID: {point.id}) ---")
        print(f"Room ID:     {payload.get('room_id')}")
        print(f"File ID:     {payload.get('file_id')}")
        print(f"Filename:    {payload.get('filename')}")
        print(f"File Type:   {payload.get('file_type')}")
        print(f"Chunk Index: {payload.get('chunk_index')}")
        print(f"Content Snippet: {str(payload.get('content', ''))[:60]}...\n")


if __name__ == "__main__":
    verify_qdrant_payloads()
