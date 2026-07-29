# check_qdrant.py
from services.vector_store import qdrant_client, COLLECTION_NAME

def verify_qdrant_payloads():
    # Retrieve stored points from the Qdrant collection
    records, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        limit=5,  # Fetch top 5 vector points
        with_payload=True,
        with_vectors=False  # Keep response clean by omitting raw vector arrays
    )

    if not records:
        print("❌ No vector points found in Qdrant collection!")
        return

    print(f"✅ Found {len(records)} points in collection '{COLLECTION_NAME}':\n")
    
    for idx, point in enumerate(records, start=1):
        print(f"--- Point {idx} (ID: {point.id}) ---")
        payload = point.payload
        print(f"Room ID:     {payload.get('room_id')}")
        print(f"File ID:     {payload.get('file_id')}")
        print(f"Filename:    {payload.get('filename')}")
        print(f"File Type:   {payload.get('file_type')}")
        print(f"Chunk Index: {payload.get('chunk_index')}")
        print(f"Content Snippet: {payload.get('content')[:60]}...\n")

if __name__ == "__main__":
    verify_qdrant_payloads()