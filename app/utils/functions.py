import os
import time
import json
# from app.utils.register_product_shopify import get_perfume_ids_from_shopify

from pinecone import Pinecone, ServerlessSpec

# from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API"))

# Define index name
index_name = "perfume-knowledge-base"

index_name_for_external = "external-perfume-knowledge-base"

index = pc.Index(index_name)
indexForExternalData = pc.Index(index_name_for_external)
# Wait for the index to be ready
while not pc.describe_index(index_name).status['ready']:
    time.sleep(1)


def prepare_text_for_embedding(perfume):
    return (
        f"{perfume['description']} "
        f"It feels like {perfume['feels_like']}. "
        f"Primary scent Goal: {perfume['primary_scent_goal']}"
        f"Occasions: {', '.join(perfume['occasions'])}. "
        f"Scent family: {', '.join(perfume['scent_family'])}. "
        f"Seasons: {', '.join(perfume['seasons'])}. "
        f"Target gender: {', '.join(perfume['target_gender'])}. "
        f"Scent vibes: {', '.join(perfume['scent_vibes'])}. "
        f"Top notes: {', '.join(perfume['top_notes'])}. "
        f"Middle notes: {', '.join(perfume['middle_notes'])}. "
        f"Bottom notes: {', '.join(perfume['bottom_notes'])}."
    )

# Function to upsert perfume data into Pinecone


def upsert_perfume_data(perfume_data, batch_size=96):
    # Process data in batches
    for i in range(0, len(perfume_data), batch_size):
        batch = perfume_data[i:i + batch_size]

        # Prepare text for embedding
        texts_to_embed = [prepare_text_for_embedding(
            perfume) for perfume in batch]

        # Generate vector embeddings for the current batch
        embeddings = pc.inference.embed(
            model="multilingual-e5-large",  # Replace with your embedding model
            inputs=texts_to_embed,
            parameters={"input_type": "passage", "truncate": "END"}
        )

        # Prepare vectors for upserting into Pinecone
        vectors = []
        for perfume, embedding in zip(batch, embeddings):
            vectors.append({
                "id": perfume["id"],
                "values": embedding["values"],  # Use the embedding vector
                "metadata": {
                    "perfume_data": json.dumps(perfume)
                }
            })

        # Upsert batch data into Pinecone
        index.upsert(vectors=vectors, namespace="perfume-namespace")
        print(
            f"""Uploaded {
                len(vectors)} perfume entries in batch {
                i //
                batch_size +
                1} to Pinecone index.""")
