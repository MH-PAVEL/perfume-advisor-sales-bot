from openai import OpenAI
from pinecone import Pinecone
# from concurrent.futures import ThreadPoolExecutor
import json
import os
from dotenv import load_dotenv
import math
# from app.utils.register_product_shopify import get_all_product_names

load_dotenv()
# Shopify API credentials
SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

# # Initialize Azure OpenAI client
# client = OpenAI(
#     # api_version="2024-08-01-preview", #3.5 turbo
#     api_version="2024-05-01-preview",  # 4omini
#     azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
#     api_key=os.getenv("OPENAI_API_KEY"),
# )

client = OpenAI(
    api_key=os.getenv("GROK_API_KEY"),
    base_url=os.getenv("GROK_ENDPOINT")
)
AI_model_to_use = "grok-3-mini"

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API"))
internal_index = pc.Index("perfume-knowledge-base")
external_index = pc.Index("external-perfume-knowledge-base")


def query_pinecone(query, perfume_no, user_goals, disliked_perfumes=[]):
    """
    Query internal and external Pinecone vector DBs with internal priority.

    Has two different search modes:
    1. Goal-based: When user_goals is not empty, distributes perfumes across goals
    2. Prompt-based: When user_goals is empty, uses pure vector search based on query text

    Maintains 75% internal / 25% external perfume split and caps total results at 24.
    """
    # Create embedding for the query text
    query_embedding = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=[query],
        parameters={"input_type": "query"}
    )[0].values

    # Constants for all search modes
    internal_ratio = 0.75
    total_limit = 24
    internal_results_final = []
    external_results_final = []
    seen_ids = set()

    # Helper function for both search modes
    def fetch_and_filter(index, namespace, filter_dict, top_k):
        try:
            response = index.query(
                namespace=namespace,
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            matches = response.get("matches", [])
        except Exception as e:
            print(f"⚠️ Pinecone Query Failed: {e}")
            return []

        results = []
        for match in matches:
            try:
                raw = match.metadata["perfume_data"]
                perfume = json.loads(raw) if isinstance(raw, str) else raw
                perfume_id = perfume.get("id") or perfume.get("title")

                if perfume_id not in seen_ids:
                    results.append(perfume)
                    seen_ids.add(perfume_id)
            except Exception as e:
                print(f"⚠️ Failed parsing perfume: {e}")
        return results

    # BRANCH 1: NO GOALS - PURE SEMANTIC SEARCH
    if not user_goals:
        print("📊 No goals provided - using pure semantic search based on query")

        # Calculate number of internal vs external perfumes
        internal_count = round(perfume_no * internal_ratio)
        external_count = perfume_no - internal_count

        # Multipliers for over-fetching to ensure quality after filtering
        internal_multiplier = 4
        external_multiplier = 4

        # Create filter that only excludes disliked perfumes
        filter_dict = {"title": {"$nin": disliked_perfumes}
                       } if disliked_perfumes else {}

        # Fetch internal perfumes
        internal_filtered = fetch_and_filter(
            internal_index,
            "perfume-namespace",
            filter_dict,
            top_k=max(internal_count * internal_multiplier, 12)
        )
        internal_results_final = internal_filtered[:internal_count]
        # internal_results_final = internal_filtered
        # Fetch external perfumes
        if external_count > 0:
            external_filtered = fetch_and_filter(
                external_index,
                "external-perfume-namespace",
                filter_dict,
                top_k=max(external_count * external_multiplier, 8)
            )
            external_results_final = external_filtered[:external_count]

    # BRANCH 2: WITH GOALS - GOAL-BASED DISTRIBUTION
    else:
        print("🎯 Using goal-based distribution across", len(user_goals), "goals")
        perfumes_per_goal = max(1, 2*(perfume_no // len(user_goals)))

        for goal in user_goals:
            # Calculate distribution per goal
            internal_goal_count = round(perfumes_per_goal * internal_ratio)
            external_goal_count = perfumes_per_goal - internal_goal_count
            print(
                f"🎯 Goal: {goal}, Internal: {internal_goal_count}, External: {external_goal_count}")

            # Create goal-specific filter
            goal_filter = {
                "primary_scent_goal": {"$in": [goal]},
                "title": {"$nin": disliked_perfumes}
            }

            # Fetch internal perfumes for this goal
            internal_filtered = fetch_and_filter(
                internal_index,
                "perfume-namespace",
                goal_filter,
                top_k=max(internal_goal_count * 4, 12)
            )
            internal_selected = internal_filtered[:internal_goal_count]
            internal_results_final.extend(internal_selected)

            # Fetch external perfumes for this goal
            if external_goal_count > 0:
                external_filtered = fetch_and_filter(
                    external_index,
                    "external-perfume-namespace",
                    goal_filter,
                    top_k=max(external_goal_count * 4, 8)
                )
                external_selected = external_filtered[:external_goal_count]
                external_results_final.extend(external_selected)

    # Combine and enforce total limit
    combined = internal_results_final + external_results_final
    if len(combined) > total_limit:
        print(f"⚠️ Capping results from {len(combined)} to {total_limit}")
        combined = combined[:total_limit]
        internal_results_final = [
            p for p in combined if p in internal_results_final]
        external_results_final = [
            p for p in combined if p in external_results_final]

    print(
        f"✅ Final count: {len(internal_results_final)} internal, {len(external_results_final)} external")
    return internal_results_final, external_results_final


def refine_user_query(goals, user_prompt):
    """Refines the user query using LLM, ensuring numbers are ignored."""
    system_prompt = (
        "You are an expert perfume recommender AI. Refine the user request by combining their goals and prompt into a highly relevant query for a perfume's vector database search. "
        "Remove any numbers mentioned in the user prompt and focus only on keywords relevant to perfume recommendations."
    )

    response = client.chat.completions.create(
        model=AI_model_to_use,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User goals: {goals}, User prompt: {user_prompt}"}
        ]
    )
    return response.choices[0].message.content.strip()


def create_perfumes_context_data(pinecone_results, user_goals):
    """Extracts, formats, and filters perfume data in a single loop."""
    filtered_perfumes = []

    for perfume_data in pinecone_results:
        # Ensure data is a valid dictionary
        if not isinstance(perfume_data, dict):
            print(f"Skipping invalid perfume data: {perfume_data}")
            continue  # Skip non-dictionaries

        # Remove unnecessary fields safely
        perfume_data.pop("image_url", None)
        perfume_data.pop("variants", None)
        perfume_data.pop("secondary_scent_goal", None)

        # Filter perfumes that match at least one of the user's goals
        if any(goal in perfume_data.get("primary_scent_goal", []) for goal in user_goals):
            filtered_perfumes.append(perfume_data)
    # with open("output.json", "w", encoding="utf-8") as f:
    #     json.dump(filtered_perfumes[:25], f, indent=4, ensure_ascii=False)
    return filtered_perfumes[:24]


def determine_user_intent(goals, user_prompt, previous_recommendations, casual_conversations, context):
    """Determines if the user is casually chatting or needs a new recommendation."""

    system_prompt = (
        "You are Joy, an AI assistant helping users explore perfumes based on their preferences. "
        "Your job is to analyze the user prompt and determine the intent accurately. "
        "**Always prioritize the 'Current User prompt' when deciding intent.**\n\n"

        "### Decision Process:\n"
        "1. **Prioritize the 'Current User prompt'.** If it clearly indicates a perfume-related request, set 'new_recommendation_needed' to True.\n"
        "   - Example: 'Create another set of perfumes for my goal.' → {'new_recommendation_needed': True}.\n"

        "2. **If the 'Current User prompt' is unrelated to perfume recommendations, classify it as casual chat.**\n"
        "   - Example: 'What is your name?' → {'casual_reply': 'My name is Joy!', 'new_recommendation_needed': False}.\n"
        "   - If the user asks about any queries about perfumes, check Perfume-related context for relevant information. user can ask perfume names in small letters, handle that situation. (ex: alchemy->ALCHEMY, fiore-> FIORÈ)\n"
        "   - Examples of questions: 'Tell me about alchemy', 'what smoky perfumes or scents are there?', 'what is the best perfume for my skin tone?'\n"

        "3. **Extract the EXACT number of perfumes requested by the user.**\n"
        "   - If the user explicitly mentions a quantity (e.g., 'Show me 3 perfumes'), use that exact number.\n"
        "   - If the user implies a quantity (e.g., 'I need a couple options', 'top five'):\n"
        "     - Convert to a SINGLE specific integer (2 for 'couple', 5 for 'five', etc.)\n"
        "     - For ranges like '3-5 perfumes', choose the middle value (4)\n"
        "   - 'requested_perfume_count' must be a single integer or null, never a range or string\n"
        "   - If no specific number is requested, set 'requested_perfume_count' to null\n"

        "4. **Use past interactions (conversation history, previous recommendations, perfume-related context) ONLY as supporting context, NOT as the primary factor.**\n"
        "   - Do NOT assume the user is asking for a new recommendation unless their current prompt explicitly or implicitly suggests it.\n"

        "5. **Always return your response in valid JSON format ONLY, without additional text or explanations.**\n\n"

        "### Response Format:\n"
        "{\n"
        "  \"new_recommendation_needed\": true/false,\n"
        "  \"casual_reply\": \"your reply if this is casual chat\",\n"
        "  \"requested_perfume_count\": integer or null\n"
        "}\n\n"

        "### Important Notes:\n"
        "- If the 'Current User prompt' is unrelated to perfumes (e.g., 'What is your name?'), classify it as casual chat.\n"
        "- Past interactions (conversation history, previous recommendations, perfume-related context) should be used ONLY for better understanding, NOT for decision-making.\n"
        "- CRITICAL: The 'requested_perfume_count' MUST be a single integer value (like 2, 3, 5) or null - never a string, array, or range.\n"
        "- Common word-to-number conversions: 'a couple' = 2, 'a few' = 3, 'several' = 4, etc.\n"
        "- Always return structured JSON responses."
    )

    chat_history = "\n".join(
        [f"User: {c['prompt']}\nJoy: {c['reply']}" for c in casual_conversations]
    ) or "No previous conversations yet."

    internal_perfumes, external_perfumes = query_pinecone(
        user_prompt, 6, goals)

    response = client.chat.completions.create(
        model=AI_model_to_use,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
                Current User goals: {goals}
                Current User prompt: {user_prompt}
                Previous recommendations: {previous_recommendations}
                Conversation history: {chat_history}
                Perfume-related context: {context + internal_perfumes + external_perfumes}
            """}
        ]
    )

    response_text = response.choices[0].message.content.strip()
    response_text = response_text.replace(
        '```json', '').replace('```', '').strip()
    try:
        intent_result = json.loads(response_text)
        # Ensure all expected keys exist
        if "casual_reply" not in intent_result:
            intent_result["casual_reply"] = None  # Default to None
        if "new_recommendation_needed" not in intent_result:
            intent_result["new_recommendation_needed"] = False

        # Handle the requested_perfume_count field properly
        if "requested_perfume_count" not in intent_result:
            intent_result["requested_perfume_count"] = None
        elif intent_result["requested_perfume_count"] is not None:
            # Ensure it's an integer
            try:
                intent_result["requested_perfume_count"] = int(
                    intent_result["requested_perfume_count"])
            except (ValueError, TypeError):
                # If not convertible to int, set to None
                intent_result["requested_perfume_count"] = None
    except json.JSONDecodeError:
        intent_result = {
            "casual_reply": "I'm not sure what you mean, but I'd love to help with perfumes!",
            "new_recommendation_needed": False,
            "requested_perfume_count": None
        }

    return intent_result


def analyze_perfumes_with_llm(internal_perfumes_context, external_perfumes_context, perfume_no, goals, user_prompt, selected_perfumes, disliked_perfumes=[], mode=""):
    """
    Uses LLM to analyze perfume context data and return top perfume names.
    Handles JSONDecodeError by stripping markdown formatting if present and provides fallback handling.
    Includes selected perfumes first in the final output.
    """
    remaining_slots = perfume_no - len(selected_perfumes)
    print("remaining_slots", remaining_slots)
    if remaining_slots <= 0:
        return selected_perfumes[:perfume_no]
    print(user_prompt, perfume_no, goals)
    # system_prompt = (
    #     f"Analyze the provided perfumes data (e.g., notes and other characteristics) and strictly select the top {remaining_slots} perfumes, no more, no less.If you return more, the user will receive an error."
    #     "that best align with the user's specified preferences, user_prompt. Do not recommend a single product twice in an array like this-> [\\'Perfume A\\', \\'Perfume B\\', \\'Perfume A\\']\\n"
    #     "Check all titles carefully and exclude any matches.\n"
    #     "- You MUST return exactly the number of perfumes requested — no more, no less.\n"
    #     "- If not enough good matches are found, still fill all slots using the best available perfumes but dont include any perfume that is already listed in selected_perfumes or disliked_perfumes.\n"
    #     "Rank the perfumes from best to least fit **within each goal group**, not globally.\n\n"
    #     "Return only a JSON array of perfume names in the correct grouped order, like:\n"

    #     """
    #     ["Perfume A", "Perfume B", "Perfume C", "Perfume D", "Perfume E", "Perfume F", "Perfume G", "Perfume H", "Perfume I", "Perfume J", "Perfume K", "Perfume L"]\n\n
    #     For 4 goals, the perfumes are grouped as follows:
    #         - Goal 1: "Perfume A", "Perfume B", "Perfume C"
    #         - Goal 2: "Perfume D", "Perfume E", "Perfume F"
    #         - Goal 3: "Perfume G", "Perfume H", "Perfume I"
    #         - Goal 4: "Perfume J", "Perfume K", "Perfume L"

    #     Perfumes for each goal must appear **together and in order** in the final output list. Avoid scattering perfumes for the same goal across different parts of the array.
    #     """
    #     "**Corner Case: If users prompt is not related to perfumes, then return ['Please provide a prompt related to perfumes'].**"
    #     If the user's prompt is not related to perfumes, (ex: what is your name, how are you doing, etc.) then return:
    # ["Please provide a prompt related to perfumes"]
    #     "**You MUST NOT return any perfume that is already listed in selected_perfumes array or disliked_perfumes array\n**"
    #     "Ensure the output is valid JSON without any markdown formatting. Return only the list of perfume names without any additional text."
    # )
    # "Return only a JSON list of perfume names in ranked order, like [\\'Best Fit Perfume\\', \\'Second Best Perfume\\', \\'Third Best Perfume\\'].\\n"
    # "[\"Perfume A\", \"Perfume B\", \"Perfume C\", \"Perfume D\"]\n\n"
    # print("len of perfumes_context_data", len(perfumes_context_data))

    # if mode == "dashboard":
    # Scent matchmaker system prompts - controls recommendation generation behavior:
    # - "dashboard" mode: Dynamically determines number of perfume recommendations based on user's request

    system_prompt = (f"""You are an expert scent matchmaker. Your job is to analyze a list of perfumes and return exactly the number of perfume(s) 
                        that the **user mentions in their prompt** as their desired number of recommendations.

                        You are given:
                        - Two list of perfumes (`internal_perfumes_context_data` and `external_perfumes_context_data`) with their notes and attributes.
                        - The user's selected goals and natural-language prompt.
                        - A list of perfumes already selected by the user.
                        - A list of perfumes the user dislikes.

                        ### 🔒 STRICT RULES
                        1. You MUST return **exactly the number of perfumes requested by the user in their prompt**. No more, no less.
                            - If user asks more than 12 perfumes, return the first 12 perfumes.
                            - IMPORTANT: Pay close attention to number words like "one", "two", "three", etc. as well as numeric digits.
                            - Examples:
                            * "suggest me one scent" → return exactly 1 perfume
                            * "show me a perfume similar to X" → return exactly 1 perfume (since "a" indicates one)
                            * "recommend three fragrances" → return exactly 3 perfumes
                            - If the user does **not** explicitly mention a specific number or use words like "a" or "one", then return 4-6 perfumes.
                        2. NEVER include perfumes that are already in the `selected_perfumes` or `disliked_perfumes` lists.
                            - selected_perfumes: {", ".join(selected_perfumes)}
                            - disliked_perfumes: {", ".join(disliked_perfumes)}
                            - suggest new perfume(s) outside of selected_perfumes and disliked_perfumes
                        3. NEVER repeat perfumes. A name must appear only once in the array.
                        4. Try to suggest 60-70% perfumes from the `internal_perfumes_context_data` list, remaining 30-40% from the `external_perfumes_context_data` list.
                        5. If the `internal_perfumes_context_data` list is empty, use the `external_perfumes_context_data` list.
                        6. NEVER hallucinate any perfume name, suggested names must be from `internal_perfumes_context_data` and `external_perfumes_context_data` lists.
                        7. If there are perfumes in `selected_perfumes` list that means user already selected those, now you have to provide new perfume(s) that are not in selected or disliked lists. 

                        ### 🎯 RECOMMENDATION STRATEGY
                            - IF GOALS ARE PROVIDED:
                            - Group the perfumes by the provided goals.
                            - For each goal, rank perfumes from best fit to least fit.
                            - Grouped perfumes must appear together in the final array.
                            - If possible, distribute perfumes equally across the goals.

                            - IF NO GOALS ARE PROVIDED:
                            - Analyze the user_prompt text carefully to understand preferences.
                            - Identify key themes such as desired scent profiles, occasions, seasons, moods, or styles.
                            - Match perfumes that align with these themes identified in the user_prompt.
                            - Organize recommendations by these inferred themes from the prompt.
                            - If the prompt lacks specific preferences, recommend a diverse selection of highly-rated perfumes covering different scent families.

                            - IF BRAND NAME IS MENTIONED IN THE PROMPT:
                            - If the user prompt includes any **brand name** (e.g., Dior, Chanel, Zara), prioritize perfumes whose `inspired_by` field matches or relates to that brand.
                            - Do **not** recommend perfumes that are unrelated to the mentioned brand unless there are very few or no good matches.
                            - This ensures the user receives aligned recommendations with their mentioned taste or expectations.

                        ### ✅ OUTPUT FORMAT
                        Return ONLY a **valid JSON array** of perfume names in the correct grouped order based on their goals or user prompt. Example:

                        [
                        "Perfume A", "Perfume B", "Perfume C", 
                        "Perfume D", "Perfume E", "Perfume F"
                        ]

                        No extra commentary, explanation, or markdown. JSON array ONLY.
                        """)
    # else:
    # Scent matchmaker system prompts - controls recommendation generation behavior:
    # - Alternative mode: Provides exactly {remaining_slots} recommendations from available inventory

    # system_prompt = (
    #     f"""You are an expert scent matchmaker. Your job is to analyze a list of perfumes and return exactly the top **{remaining_slots}** perfume(s)
    #     that best match the user's goals and preferences.

    #     You are given:
    #     - Two list of perfumes (`internal_perfumes_context_data` and `external_perfumes_context_data`) with their notes and attributes.
    #     - The user's selected goals and natural-language prompt.
    #     - A list of perfumes already selected by the user.
    #     - A list of perfumes the user dislikes.

    #     ### 🔒 STRICT RULES
    #     1. You MUST return **exactly {remaining_slots} perfume(s)**. No more, no less. If you return more, the response will be rejected.
    #     2. NEVER include perfumes that are already in the `selected_perfumes` or `disliked_perfumes` lists.
    #         - selected_perfumes: {", ".join(selected_perfumes)}
    #         - disliked_perfumes: {", ".join(disliked_perfumes)}
    #         - suggest {remaining_slots} new perfume(s) outside of selected_perfumes and disliked_perfumes
    #     3. NEVER repeat perfumes. A name must appear only once in the array.
    #     4. Try to suggest 60-70% perfumes from the `internal_perfumes_context_data` list, remaining 30-40% from the `external_perfumes_context_data` list.
    #     5. If the `internal_perfumes_context_data` list is empty, use the `external_perfumes_context_data` list.
    #     6. NEVER hallucinate any perfume name, suggested names must be from `internal_perfumes_context_data` and `external_perfumes_context_data` lists.
    #     7. If there are perfumes in `selected_perfumes` list that means user already selected those, now you have to provide {remaining_slots} new perfume(s) that are not in selected or disliked lists.

    #     ### 🎯 GOAL-BASED GROUPING
    #     - Group the perfumes by the provided goals.
    #     - For each goal, rank perfumes from best fit to least fit.
    #     - Grouped perfumes must appear together in the final array. (e.g., Perfumes for "boost confidence" should come first, then "smell unique", etc.)
    #     - If possible, distribute perfumes equally across the goals.
    #         - For example, if there are 3 goals and {remaining_slots} total slots, assign approximately {remaining_slots // 3} perfumes to each goal.
    #         - If equal distribution isn't cleanly possible, distribute as evenly as possible that best aligns with the user's prompt.

    #     ### 🏷 BRAND-SPECIFIC FILTERING (if applicable)
    #     - If the user prompt includes any **brand name** (e.g., Dior, Chanel, Zara), prioritize perfumes whose `inspired_by` field matches or relates to that brand.
    #     - Do **not** recommend perfumes that are unrelated to the mentioned brand unless there are very few or no good matches.
    #     - This ensures the user receives aligned recommendations with their mentioned taste or expectations.

    #     ### ✅ OUTPUT FORMAT
    #     Return ONLY a **valid JSON array** of perfume names in the correct grouped order based on their goals. Example:

    #     [
    #     "Perfume A", "Perfume B", "Perfume C",
    #     "Perfume D", "Perfume E", "Perfume F"
    #     ]

    #     No extra commentary, explanation, or markdown. JSON array ONLY.

    #     """
    # )
    # print("system_prompt", system_prompt)
    # 4. If fewer good options are available, still return {remaining_slots} perfumes by using the best available remaining perfumes.
    # 6. If there are perfumes in `selected_perfumes` list that means user already selected those, now you have to provide {remaining_slots} new perfume(s) that are not selected or disliked.
    try:
        response = client.chat.completions.create(
            model=AI_model_to_use,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps({
                    "goals": goals,
                    "user_prompt": user_prompt,
                    # "selected_perfumes": selected_perfumes,
                    "internal_perfumes_context_data": internal_perfumes_context,
                    "external_perfumes_context_data": external_perfumes_context,
                    # "disliked_perfumes": disliked_perfumes
                }, ensure_ascii=False)}
            ]
        )

        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Received empty response from LLM.")

        suggested_perfumes = response.choices[0].message.content.strip()
        suggested_perfumes = suggested_perfumes.replace(
            '```json', '').replace('```', '').strip()

        try:
            suggested_list = json.loads(suggested_perfumes)
            print("MFFFF", suggested_list, selected_perfumes)
            return selected_perfumes + suggested_list
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"LLM Response: {suggested_perfumes}")
            return selected_perfumes
    except Exception as e:
        print(f"Error during LLM analysis: {e}")
        return selected_perfumes


# def landing_page_scent_recommendation(perfume_no, goals, user_prompt, selected_perfumes, disliked_perfumes=[]):
#     """Main function to recommend perfumes from internal & external sources."""
#     # print("disliked from landing page", disliked_perfumes)
#     internal_perfumes, external_perfumes = query_pinecone(
#         user_prompt + ", " + ",".join(goals), perfume_no, goals, disliked_perfumes)

#     final_recommendations = analyze_perfumes_with_llm(
#         internal_perfumes,
#         external_perfumes, perfume_no, goals, user_prompt, selected_perfumes, disliked_perfumes
#     )
#     # print("final_recommendations initially", final_recommendations)

#     # Remove duplicates while preserving order
#     seen = set()
#     final_recommendations = [name for name in final_recommendations if not (
#         name in seen or seen.add(name))]
#     print("final_recommendations when duplication removed", final_recommendations)

#     # Retry if count is not as expected
#     if len(final_recommendations) != perfume_no:
#         final_recommendations = analyze_perfumes_with_llm(
#             internal_perfumes,
#             external_perfumes, perfume_no, goals, user_prompt, final_recommendations, disliked_perfumes
#         )
#         print("final_recommendations when re-analyzed", final_recommendations)
#     filtered_perfumes_internal_context_data, filtered_perfumes_external_context_data = filter_perfume_context(
#         internal_perfumes, external_perfumes, final_recommendations
#     )
#     print("internal perfumes", len(filtered_perfumes_internal_context_data), "external perfumes",
#           len(filtered_perfumes_external_context_data))
#     return final_recommendations, filtered_perfumes_internal_context_data, filtered_perfumes_external_context_data
#     # return final_recommendations, [], []

def landing_page_scent_recommendation(perfume_no, goals, user_prompt, selected_perfumes, disliked_perfumes=[], mode=""):
    """Main function to recommend perfumes from internal & external sources."""

    internal_perfumes, external_perfumes = query_pinecone(
        user_prompt + ", " +
        ",".join(goals), perfume_no, goals, disliked_perfumes
    )

    def clean_and_dedupe(recommendations, selected, disliked):
        # Remove perfumes already in selected/disliked
        filtered = [
            p for p in recommendations
            if p not in selected and p not in disliked
        ]
        # Remove duplicates, case-insensitive
        seen = set()
        unique = [p for p in filtered if not (
            p.lower() in seen or seen.add(p.lower()))]
        return unique

    # First attempt
    llm_suggestions = analyze_perfumes_with_llm(
        internal_perfumes, external_perfumes,
        perfume_no, goals, user_prompt, selected_perfumes, disliked_perfumes, mode
    )

    cleaned = clean_and_dedupe(
        llm_suggestions, selected_perfumes, disliked_perfumes)
    final_recommendations = (selected_perfumes + cleaned)[:perfume_no]

    # # Retry only if not enough perfumes after cleaning
    # if len(final_recommendations) < perfume_no:
    #     retry_selected = final_recommendations[:]
    #     retry_remaining = perfume_no - len(retry_selected)

    #     print(
    #         f"⚠️ Retry needed, only got {len(final_recommendations)}. Trying again...")

    #     new_llm_suggestions = analyze_perfumes_with_llm(
    #         internal_perfumes, external_perfumes,
    #         perfume_no, goals, user_prompt, retry_selected, disliked_perfumes, mode
    #     )
    #     cleaned_retry = clean_and_dedupe(
    #         new_llm_suggestions, retry_selected, disliked_perfumes)
    #     final_recommendations = (retry_selected + cleaned_retry)[:perfume_no]

    print("✅ Final recommendations:", final_recommendations)

    # Filter context for returned perfumes
    filtered_perfumes_internal_context_data, filtered_perfumes_external_context_data = filter_perfume_context(
        internal_perfumes, external_perfumes, final_recommendations
    )

    print("internal perfumes", len(filtered_perfumes_internal_context_data),
          "external perfumes", len(filtered_perfumes_external_context_data))

    return final_recommendations, filtered_perfumes_internal_context_data, filtered_perfumes_external_context_data


def delete_perfumes_from_pinecone(perfume_list):
    """
    Deletes perfumes from the Pinecone vector database based on their IDs.

    Args:
        perfume_list (list): A list of dictionaries containing perfume data, including their 'id'.

    Returns:
        dict: A dictionary containing success status and deleted IDs.
    """
    try:
        # Extract IDs from the perfume list
        perfume_ids = [perfume["id"] for perfume in perfume_list]

        # Perform deletion from Pinecone
        if len(perfume_ids) > 0:
            print(
                f"Deleting {len(perfume_ids)} perfumes from Pinecone...{perfume_ids}")
            external_index.delete(
                ids=perfume_ids, namespace="external-perfume-namespace")

    except Exception as e:
        print(f"Error deleting perfumes from Pinecone: {e}")


def filter_perfume_context(internal_perfumes, external_perfumes, perfume_list):
    """
    Filters internal and external perfume data to include only the perfumes
    that match the given list of perfume names.

    Args:
        internal_perfumes (list): List of dictionaries containing internal perfume data.
        external_perfumes (list): List of dictionaries containing external perfume data.
        perfume_list (list): List of perfume names that need to be filtered.

    Returns:
        tuple: Two lists containing filtered internal perfumes and filtered external perfumes.
    """
    filtered_internal_perfumes = [
        perfume for perfume in internal_perfumes if perfume.get("title") in perfume_list]

    # external_perfumes_json = json.loads(external_perfumes)
    # print(external_perfumes_json)
    filtered_external_perfumes = [
        perfume for perfume in external_perfumes if perfume.get("title") in perfume_list]

    return filtered_internal_perfumes, filtered_external_perfumes


def explain_perfume_recommendations(perfume_list, goals, user_prompt, perfumes_context_data):
    """
    Generates a markdown-formatted explanation for why specific perfumes were recommended.

    Args:
        perfume_list (list): List of perfume names recommended.
        goals (list): Goals provided by the user.
        user_prompt (str): The user's personal prompt.
        perfumes_context_data (list): List of filtered perfume dictionaries.

    Returns:
        str: A markdown-formatted explanation of the perfume recommendations.
    """
    try:

        system_prompt = (
            "You are Joy, an expert fragrance consultant for Evoked. Your task is to explain why each of the 12 recommended perfumes "
            "was chosen based on the provided details.\n\n"

            "Your response must be well-structured, engaging, and formatted in markdown. Follow this exact format:\n\n"

            "**Introduction:**\n"
            "- Start with a short, welcoming introduction like:\n"
            "  \"Here's why I've picked these 12 scents just for you! Each fragrance aligns perfectly with your preferences and goals.\"\n\n"

            "**Perfume Breakdown (Mandatory for ALL 12 perfumes):**\n"
            "- **For each perfume:**\n"
            "  1. **Bold the perfume name** and give a short, engaging one-line summary of its appeal.\n"
            "  2. **List three key scent characteristics** using a numbered format:\n"
            "     - Each point should have:\n"
            "       - A **bold subheading** summarizing the note.\n"
            "       - A short, engaging explanation of how that note contributes to the perfume's experience.\n\n"
            "**Rules & Constraints:**\n"
            "1. **DO NOT SKIP ANY PERFUME.** You must explain all 12 perfumes and don't explain any perfumes twice.\n"
            "2. **DO NOT SUMMARIZE OR SHORTEN THE RESPONSE.** Each perfume must have its own full breakdown.\n"
            "3. **MAINTAIN A FRIENDLY & EXPERT TONE.** The user should feel excited and confident about their perfume choices.\n"
            "4. **DO NOT add extra commentary or make assumptions.** Only use the provided perfume data to generate responses.\n\n"

            "Now, generate the structured explanation for all 12 perfumes."
        )

        user_input = json.dumps({
            "goals": goals,
            "user_prompt": user_prompt,
            "perfume_list": perfume_list,
            "perfumes_context_data": perfumes_context_data
        })

        response = client.chat.completions.create(
            model=AI_model_to_use,
            max_tokens=2500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Received empty response from LLM.")

        explanation = response.choices[0].message.content.strip()

        return explanation
    except Exception as e:
        print(f"Error generating recommendation summary: {e}")
        return "**Oops! Something went wrong while generating your recommendations. Please try again later.**"


def generate_recommendation_summary(perfume_list, goals, user_prompt, perfumes_context_data):
    """
    Generates a markdown-formatted recommendation summary using OpenAI LLM,
    incorporating perfume context details.

    Args:
        perfume_list (list): List of recommended perfume names.
        goals (list): Goals provided by the user.
        user_prompt (str): The user's personal prompt.
        perfumes_context_data (list): Contextual perfume data.

    Returns:
        str: A markdown-formatted recommendation summary.
    """
    return generate_recommendation_summary_from_conversation(perfume_list, goals, user_prompt, perfumes_context_data, users_previous_prompts=[])


def generate_recommendation_summary_from_conversation(perfume_list, goals, user_prompt, perfumes_context_data, users_previous_prompts):
    """
    Generates a markdown-formatted recommendation summary using OpenAI LLM,
    incorporating perfume context details and considering the user's previous prompts.

    Args:
        perfume_list (list): List of recommended perfume names.
        goals (list): Goals provided by the user.
        user_prompt (str): The user's personal prompt.
        perfumes_context_data (list): Contextual perfume data.
        users_previous_prompts (list): List of previous prompts from the user.

    Returns:
        str: A markdown-formatted recommendation summary.
    """
    try:
        ready_to_ship_set = {
            "NILA", "WILDFIRE", "TEMPEST", "MEGAMI", "TAJ", "OBSIDIAN", "CITADEL", "SUCCEXA",
            "OUDAMORE", "VOYAGEUR", "DAVINCI", "PELAGIOS", "ELARA", "YOUNGBLOOD", "JÓLIE",
            "BIJOÚ", "MYSA", "INARA", "VIRAGO", "FELICITY", "SEVGI", "KALONE", "FAMORÉ",
            "NOIRÉ", "ALCHEMY", "NOVA", "VALKYRIE", "ELYSIAN", "ASTRALIS", "SAHARA",
            "NOCTURNAL", "KITARA", "BRAVURA", "DOMINA", "AMORIS", "GLIMMER", "ZAVARA", "FIORÈ"
        }

        # Extract relevant details for each recommended perfume
        perfume_details = []
        for perfume in perfumes_context_data:
            if perfume["title"] in perfume_list:
                availability = "✅ In Stock - Ready to ship!" if perfume[
                    "title"] in ready_to_ship_set else "🛠️ Custom-made - Requires 3-5 days to craft."

                perfume_summary = (
                    f"**{perfume['title']}** ({availability})\n"
                    f"   - **Top Notes:** {', '.join(perfume['top_notes'])}\n"
                    f"   - **Middle Notes:** {', '.join(perfume['middle_notes'])}\n"
                    f"   - **Base Notes:** {', '.join(perfume['bottom_notes'])}\n"
                    f"   - **Feels Like:** {perfume['feels_like']}\n"
                    f"   - **Best for:** {', '.join(perfume['occasions'])} ({', '.join(perfume['seasons'])})\n"
                    f"   - **Scent Goal:** {', '.join(perfume['primary_scent_goal'])}\n"
                )
                perfume_details.append(perfume_summary)

        perfume_summary_text = "\n".join(perfume_details)

        # Combine previous user prompts to maintain context
        previous_prompts_text = "\n".join(
            [f"- {p}" for p in users_previous_prompts]) if users_previous_prompts else "No prior questions."

        system_prompt = (
            "You are Joy, an expert fragrance consultant for a luxury perfume company named Evoked.\n"
            "Your task is to provide a **concise, engaging, and persuasive** recommendation summary in markdown format.\n"
            "Your response should feel **personalized, natural, and encourage the user to purchase**.\n\n"

            "### **Follow this structure:**\n\n"
            "- Acknowledge the user's goals and reference their preferences.\n"
            f"- Mention **all {len(perfume_list)} perfumes**, dynamically assigning their availability.\n"
            "- Briefly summarize the key characteristics of each perfume.\n"
            f"- Encourage selecting all **{len(perfume_list)} scents** (mentioning that *95% of customers find their perfect match this way*).\n"
            "- If there are no goals, focus on the preferences mentioned in user_prompt instead.\n"
            "- Consider the user's **previous questions** when responding.\n"
            "- Create urgency using phrases like *\"Don't miss out!\"* or *\"These are our top picks!\"*.\n"
            "- End with:\n\n"
            "*\"If you’d like me to make any changes for you or have any questions, please just reply back! :)\"*\n\n"
        )

        user_input = f"""
        **User Goals:** {', '.join(goals)}
        **User Prompt:** {user_prompt}
        **Previous Questions:** 
        {previous_prompts_text}
        **Perfume Recommendations:**
        {perfume_summary_text}
        """

        response = client.chat.completions.create(
            model=AI_model_to_use,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Received empty response from LLM.")

        recommendation_summary = response.choices[0].message.content.strip()

        return recommendation_summary

    except Exception as e:
        print(f"Error generating recommendation summary: {e}")
        return "**Oops! Something went wrong while generating your recommendations. Please try again later.**"
