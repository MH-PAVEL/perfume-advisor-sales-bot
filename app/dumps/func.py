# def query_pinecone(query, perfume_no):
#     """Query both internal and external Pinecone vector DBs."""
#     internal_top_k = max(int(perfume_no * 0.7), 1)  # 70% internal
#     external_top_k = min(perfume_no - internal_top_k, 6)  # 30% external, max 6

#     query_embedding = pc.inference.embed(
#         model="multilingual-e5-large",
#         inputs=[query],
#         parameters={"input_type": "query"}
#     )[0].values

#     with ThreadPoolExecutor() as executor:
#         future_internal = executor.submit(
#             internal_index.query, namespace="perfume-namespace", vector=query_embedding, top_k=internal_top_k, include_metadata=True
#         )
#         future_external = executor.submit(
#             external_index.query, namespace="external-perfume-namespace", vector=query_embedding, top_k=external_top_k, include_metadata=True
#         )

#         try:
#             internal_results = future_internal.result()
#         except Exception as e:
#             print(f"⚠️ Pinecone Internal Query Failed: {e}")
#             internal_results = {"matches": []}  # Fallback to empty results

#         try:
#             external_results = future_external.result()
#         except Exception as e:
#             print(f"⚠️ Pinecone External Query Failed: {e}")
#             external_results = {"matches": []}  # Fallback to empty results

#     # Convert internal results' perfume_data from JSON string to dictionary
#     internal_parsed_results = []
#     internal_parsed_results = [
#         json.loads(match.metadata["perfume_data"]) for match in internal_results.get("matches", [])
#         if "perfume_data" in match.metadata
#     ]

#     # Extract only metadata from external results to transform via LLM
#     external_metadata = [
#         match.metadata for match in external_results.get("matches", [])]

#     return internal_parsed_results, external_metadata


# try:
#     pc.create_index(
#         name=index_name,
#         dimension=1024,
#         metric="cosine",
#         spec=ServerlessSpec(cloud='aws', region="us-east-1")
#     )
# except Exception as e:
#     if "already exists" not in str(e).lower():
#         raise e

# index = pc.Index(index_name)


# def transform_external_perfume_data(external_perfumes):
#     """Converts external perfume data into the internal format using LLM."""
#     shopify_product_names = get_all_product_names()
#     print(str(shopify_product_names))

#     system_prompt = (
#         "You are an AI assistant trained to standardize perfume data formats. "
#         "Convert the provided external perfume data into the following JSON format, ensuring it matches the internal schema:\n"
#         "\nThis is our existing perfume names: " +
#         str(shopify_product_names) + "\n"
#         "{\n"
#         '    "id": "string",\n'
#         '    "title": "A luxurious, unique perfume name.",\n'
#         '    "description": "Rewrite the description in a refined, engaging tone while preserving all original details. Ensure it reads naturally as a perfume description and does not contain any references to brand names or unrelated content.",\n'
#         '    "feels_like": "A short phrase capturing the sensory experience of this perfume.",\n'
#         '    "primary_scent_goal": ["Select one from: smell unique, boost confidence, increase attraction, improve mood, reduce stress, sleep better."],\n'
#         '    "occasions": ["List of suitable occasions where this scent fits best."],\n'
#         '    "scent_family": ["Ensure all original scent accords are retained without simplification."],\n'
#         '    "seasons": ["List of suitable seasons for this fragrance."],\n'
#         '    "target_gender": ["Male", "Female", "Unisex"],\n'
#         '    "scent_vibes": ["List of scent vibes (e.g., Fresh, Spicy, Warm, Woody, Sweet)."],\n'
#         '    "top_notes": ["Extract and list the top notes from the provided description. If missing, infer based on the scent profile."],\n'
#         '    "middle_notes": ["Extract and list the middle notes. If missing, infer based on the scent profile."],\n'
#         '    "bottom_notes": ["Extract and list the base notes. If missing, infer based on the scent profile."],\n'
#         "}\n\n"
#         "Important guidelines:\n"
#         "- The generated title must be a luxurious and unique perfume name, resembling our existing product names. (Do not use our existing products names exactly it might create conflition).\n"
#         "- Do not use generic names like 'Passion' or 'Freedom'. Create a sophisticated, one-word name similar to 'NILA' or 'OUDAMORE'.\n"
#         "- Ensure all main accords are fully represented in the 'scent_family' field without missing key details.\n"
#         "- Rewrite descriptions elegantly while keeping all key details. Do not alter the original meaning or introduce metaphors that distort the intent.\n"
#         "- Avoid adding any extra details not present in the original description.\n"
#         "- Remove irrelevant content like 'Read about this perfume in other languages'.\n"
#         "- Ensure the 'scent_family' retains all original main accords without removing any descriptors.\n"
#         "- Ensure that 'top_notes', 'middle_notes', and 'bottom_notes' are never empty. If the source does not specify them, infer them based on the main accords.\n"
#         "- The 'description' should highlight all primary scent components, ensuring a detailed but natural narrative.\n"
#         "- Only provide a valid JSON as output, without any extra text or formatting.\n"
#     )

#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": json.dumps(
#                     external_perfumes, ensure_ascii=False)}
#             ]
#         )

#         llm_response = response.choices[0].message.content.strip()

#         # Debugging: Print LLM response before parsing
#         # print("LLM Raw Response:", llm_response)

#         # Remove Markdown formatting if present
#         llm_response = llm_response.replace(
#             "```json", "").replace("```", "").strip()

#         return json.loads(llm_response)

#     except json.JSONDecodeError as e:
#         print(f"JSON Decode Error: {e}")
#         print(f"LLM Response: {llm_response}")  # Debugging
#         return []

#     except Exception as e:
#         print(f"Error transforming external perfumes: {e}")
#         return []


# def create_perfumes_context_data(pinecone_results):
#     """Extracts and formats perfume data, ensuring unnecessary fields are removed if present."""
#     perfumes_context_data = []

#     for perfume_data in pinecone_results:
#         # Ensure data is a valid dictionary
#         if not isinstance(perfume_data, dict):
#             print(f"Skipping invalid perfume data: {perfume_data}")
#             continue  # Skip non-dictionaries

#         # Remove unnecessary fields safely
#         perfume_data.pop("image_url", None)
#         perfume_data.pop("variants", None)
#         perfume_data.pop("secondary_scent_goal", None)

#         perfumes_context_data.append(perfume_data)

#     return perfumes_context_data


# def clean_perfume_data(perfume_data):
#     """Removes unnecessary fields from perfume data."""
#     if isinstance(perfume_data, dict):
#         perfume_data.pop("image_url", None)
#         perfume_data.pop("variants", None)
#         perfume_data.pop("secondary_scent_goal", None)
#     return perfume_data


# def query_pinecone(query, perfume_no, user_goals):
#     """Query both internal and external Pinecone vector DBs with internal priority and filter based on user goals."""

#     query_embedding = pc.inference.embed(
#         model="multilingual-e5-large",
#         inputs=[query],
#         parameters={"input_type": "query"}
#     )[0].values

#     with ThreadPoolExecutor() as executor:
#         future_internal = executor.submit(
#             internal_index.query, namespace="perfume-namespace", vector=query_embedding, top_k=perfume_no*2, include_metadata=True,
#             filter={"priamry_scent_goal": {"$in": user_goals}}
#         )

#         try:
#             internal_results = future_internal.result()
#         except Exception as e:
#             print(f"⚠️ Pinecone Internal Query Failed: {e}")
#             internal_results = {"matches": []}  # Fallback to empty results

#     # Convert internal results' perfume_data from JSON string to dictionary and apply filtering
#     filtered_internal_results = [
#         clean_perfume_data(json.loads(match.metadata["perfume_data"]))
#         for match in internal_results.get("matches", [])
#         if "perfume_data" in match.metadata and any(
#             goal in json.loads(match.metadata["perfume_data"]).get(
#                 "primary_scent_goal", [])
#             for goal in user_goals
#         )
#     ]
#     print("filtered_internal_results", filtered_internal_results)
#     remaining_slots = (perfume_no*3) - len(filtered_internal_results)
#     print("remaining_slots", remaining_slots)
#     filtered_external_results = []
#     # Only fetch external perfumes if internal ones are insufficient
#     if remaining_slots > 0:
#         with ThreadPoolExecutor() as executor:
#             future_external = executor.submit(
#                 external_index.query, namespace="external-perfume-namespace", vector=query_embedding, top_k=remaining_slots*8, include_metadata=True,
#                 filter={"priamry_scent_goal": {"$in": user_goals}}
#             )

#             try:
#                 external_results = future_external.result()
#                 # print("len ex prod", external_results)
#             except Exception as e:
#                 print(f"⚠️ Pinecone External Query Failed: {e}")
#                 external_results = {"matches": []}  # Fallback to empty results

#             # Convert external results and apply filtering
#             filtered_external_results = [
#                 json.loads(match["metadata"]["perfume_data"])
#                 for match in external_results.get("matches", [])
#                 if "metadata" in match and "perfume_data" in match["metadata"]
#                 and isinstance(json.loads(match["metadata"]["perfume_data"]), dict)
#                 and any(goal in json.loads(match["metadata"]["perfume_data"]).get("primary_scent_goal", []) for goal in user_goals)

#             ]
#     if len(filtered_external_results) > (20 - remaining_slots):
#         filtered_external_results = filtered_external_results[:(
#             20 - remaining_slots)]

#     return filtered_internal_results, filtered_external_results

#    "4. **If the user mentions specific perfumes they LIKE from the Previous recommendations list:**\n"
#    "   - Extract the mentioned perfumes and pass them as 'liked_perfumes'.\n"
#    "   - Example:\n"
#    "     User Prompt: 'I liked SUCCEXA, YOUNGBLOOD, and VOYAGEUR. Keep them in my next set.'\n"
#    "     Response: {'liked_perfumes': ['SUCCEXA', 'YOUNGBLOOD', 'VOYAGEUR'], 'new_recommendation_needed': True}.\n"

#    "5. **If the user mentions 3-4 perfumes they DISLIKE from the Previous recommendations list:**\n"
#    "   - Remove those perfumes from the previous recommendations and pass the remaining perfumes as 'liked_perfumes'.\n"
#    "   - Example:\n"
#    "     User Prompt: 'I didn't like NILA, TAJ, and ZAVARA. Give me a new set without them.'\n"
# #    "     Response: {'liked_perfumes': ['SUCCEXA', 'YOUNGBLOOD', 'VOYAGEUR', 'VIGORE', 'GRAVITÉ', 'AURAVIO', 'AQUAFORGE', 'AQUASPORT', 'ECLICIA'], 'new_recommendation_needed': True}.\n"
# "4. **If the user just requests a new set without specifying likes or dislikes:**\n"
# "   - Set 'liked_perfumes' as an empty list ([]).\n"
# "   - Example:\n"
# "     User Prompt: 'Make me a completely fresh set of perfumes.'\n"
# "     Response: {'liked_perfumes': [], 'new_recommendation_needed': True}.\n"
