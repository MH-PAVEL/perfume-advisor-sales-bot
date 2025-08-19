import random
from app.utils.register_product_shopify import register_external_perfumes_in_shopify
from app.utils.landing_page_ai import landing_page_scent_recommendation, generate_recommendation_summary, generate_recommendation_summary_from_conversation, explain_perfume_recommendations, determine_user_intent
import datetime
from app.utils.product_journal import get_journal_response, get_summary_response
from app.utils.life_journal import get_life_journal_response, generate_life_journal_summary

from datetime import datetime
# from app.utils.background_threads import register_external_perfumes_background
from app.utils.update_email import update_email_in_collection
from bson import ObjectId
from flask import request, jsonify, current_app as app

db = app.db


# Endpoint for updating email in landing_page_prompt
@app.route('/flask/api/update_email_landing/<string:doc_id>', methods=['POST'])
def update_email_landing(doc_id):
    return update_email_in_collection(doc_id, db.landing_page_prompt)

# Endpoint for updating email in home_page_conversation


@app.route('/flask/api/update_email_home/<string:doc_id>', methods=['POST'])
def update_email_home(doc_id):
    return update_email_in_collection(doc_id, db.home_page_conversation)


# Landing page route to get perfume recommendation

@app.route('/flask/api/landing-page-recommend-perfume', methods=['POST'])
def recommend_perfume():
    try:
        data = request.get_json()
        perfume_no = data.get("perfume_no")
        goals = data.get("goals")
        user_prompt = data.get("user_prompt")
        selected_perfumes = data.get("selected_perfumes")

        recommendations, _, filtered_perfumes_external_context_data = landing_page_scent_recommendation(
            perfume_no, goals, user_prompt, selected_perfumes)

        if recommendations == ['Please provide a prompt related to perfumes']:
            return jsonify({
                "success": False,
                "error": "It looks like your prompt isn't related to perfumes. Please provide details about the type of scent you're looking for, and I'd be happy to help!"
            }), 400  # Bad Request

        _ = register_external_perfumes_in_shopify(
            filtered_perfumes_external_context_data)

        # Add data to MongoDB
        result = db.landing_page_prompt.insert_one({
            "user_prompt": user_prompt,
            "goals": goals,
            "perfume_no": perfume_no,
            "recommendations": recommendations,
            "selected_perfumes": selected_perfumes,
            "external_perfumes": filtered_perfumes_external_context_data,
            "created_at": datetime.now()
        })
        doc_id = result.inserted_id
        return jsonify({"success": True, "recommendations": recommendations, "doc_id": str(doc_id)}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Home page route to get perfume recommendation (initiate conversation)
@app.route('/flask/api/home-page-recommend-perfume', methods=['POST'])
def home_page_initiate_conversation():
    try:
        data = request.get_json()
        goals = data.get("goals", [])
        user_prompt = data.get("user_prompt")
        # print("goals", goals, "user_prompt", user_prompt)
        # return jsonify({"success": True}), 200
        # num_recommendations = random.randint(1, 6)
        num_recommendations = 12
        # Step 1: Get perfume recommendations (immediate response)
        try:
            recommendations, filtered_perfumes_internal_context_data, filtered_perfumes_external_context_data = landing_page_scent_recommendation(
                num_recommendations, goals, user_prompt, [])
            print("reccommedation", recommendations)
        except Exception as e:
            print("recommendation error from home page", e)
            return jsonify({
                "success": False,
                "error": f"Error while generating recommendations: {str(e)}"
            }), 500

        if recommendations == ['Please provide a prompt related to perfumes']:
            return jsonify({
                "success": False,
                "error": "It looks like your prompt isn't related to perfumes. Please provide details about the type of scent you're looking for, and I'd be happy to help!"
            }), 400  # Bad Request

        # Step 2: Generate `recommendation_summary` (run immediately)
        try:
            recommendation_summary = generate_recommendation_summary(
                recommendations, goals, user_prompt,
                filtered_perfumes_internal_context_data +
                filtered_perfumes_external_context_data
            )
        except Exception as e:
            print("recommendation_summary error", e)
            return jsonify({
                "success": False,
                "error": f"Error while summarizing recommendations: {str(e)}"
            }), 500

        # Step 3: Store initial conversation data **without explanation_of_perfumes**
        result = db.home_page_conversation.insert_one({
            "users_previous_prompts": [user_prompt],
            "goals": goals,
            "recommendations": recommendations,
            "recommendation_summary": recommendation_summary,
            "context": filtered_perfumes_internal_context_data +
            filtered_perfumes_external_context_data,
            "created_at": datetime.now()
        })
        conversation_id = result.inserted_id

        # Step 4: Register external perfumes in Shopify

        _ = register_external_perfumes_in_shopify(
            filtered_perfumes_external_context_data)

        # Step 5: Send immediate response
        return jsonify({
            "success": True,
            "recommendations": recommendations,
            "recommendation_summary": recommendation_summary,
            "context": filtered_perfumes_internal_context_data + filtered_perfumes_external_context_data,
            "conversation_id": str(conversation_id)
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/flask/api/dashboard/conversation', methods=['POST'])
def handle_dashboard_AI_conversation():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        user_prompt = data.get("user_prompt")
        goals = data.get("goals", [])
        selected_perfumes = data.get("selected_perfumes", [])
        disliked_perfumes = data.get("disliked_perfumes", [])
        # num_recommendations = random.randint(1, 12)
        num_recommendations = 12

        if not user_id or not user_prompt:
            return jsonify({"success": False, "error": "user_id and user_prompt are required"}), 400

        # Check if conversation exists
        conversation = db.dashboard_conversations.find_one(
            {"user_id": user_id})

        def append_message(user, bot=None, recommendations=None, summary=None):
            msg = [{"type": "user", "text": user}]
            if recommendations:
                msg.append({
                    "type": "bot", "text": summary, "recommendations": recommendations, "mode": "recommendation"
                })
            elif bot:
                msg.append({"type": "bot", "text": bot, "mode": "casual"})
            return msg

        if conversation:
            messages = conversation.get("messages", [])
            context = conversation.get("context", [])

            # Extract previous conversations for context - limited to last 4 exchanges to manage token limits
            MAX_HISTORY = 6
            casual_conversations = []

            # Build conversation history from messages array
            user_messages = []
            bot_responses = []

            for msg in messages:
                if msg["type"] == "user":
                    user_messages.append(msg["text"])
                elif msg["type"] == "bot" and msg.get("mode") == "casual":
                    bot_responses.append(msg["text"])

            # Create conversation pairs, limited to MAX_HISTORY recent exchanges
            for i in range(min(len(user_messages), len(bot_responses))):
                casual_conversations.append({
                    "prompt": user_messages[i],
                    "reply": bot_responses[i]
                })

            # Limit to most recent MAX_HISTORY conversations
            casual_conversations = casual_conversations[-MAX_HISTORY:] if len(
                casual_conversations) > MAX_HISTORY else casual_conversations

            # Get previous recommendations
            previous_recommendations = [m["recommendations"]
                                        for m in messages if m.get("mode") == "recommendation"]
            previous_recommendations = previous_recommendations[-1] if previous_recommendations else [
            ]

            # Pass conversation history to determine_user_intent
            intent_result = determine_user_intent(
                goals, user_prompt, previous_recommendations, casual_conversations, context
            )

            if intent_result.get("new_recommendation_needed", True):
                # Use LLM-detected count if specified, otherwise use default
                recommendation_count = intent_result.get(
                    "requested_perfume_count") or num_recommendations

                recommendations, internal_context, external_context = landing_page_scent_recommendation(
                    recommendation_count, goals, user_prompt, selected_perfumes, disliked_perfumes, mode="dashboard"
                )
                combined_context = internal_context + external_context

                recommendation_summary = generate_recommendation_summary_from_conversation(
                    recommendations, goals, user_prompt, combined_context, user_messages[-MAX_HISTORY:]
                )

                _ = register_external_perfumes_in_shopify(external_context)

                new_messages = append_message(
                    user_prompt, summary=recommendation_summary, recommendations=recommendations)

                db.dashboard_conversations.update_one(
                    {"_id": conversation["_id"]},
                    {
                        "$set": {
                            "goals": goals,
                            "context": combined_context,
                            "updated_at": datetime.now()
                        },
                        "$push": {"messages": {"$each": new_messages}}
                    }
                )

                return jsonify({
                    "success": True,
                    "mode": "continue_recommendation",
                    "recommendations": recommendations,
                    "recommendation_summary": recommendation_summary,
                    "context": combined_context,
                    "conversation_id": str(conversation["_id"])
                }), 200

            elif intent_result.get("casual_reply"):
                casual_reply = intent_result["casual_reply"]
                new_messages = append_message(user_prompt, bot=casual_reply)

                db.dashboard_conversations.update_one(
                    {"_id": conversation["_id"]},
                    {
                        "$set": {"updated_at": datetime.now()},
                        "$push": {"messages": {"$each": new_messages}}
                    }
                )

                return jsonify({
                    "success": True,
                    "mode": "continue_casual",
                    "casual_reply": casual_reply,
                    "conversation_id": str(conversation["_id"])
                }), 200

            return jsonify({"success": False, "error": "Could not determine user intent."}), 400

        else:
            # For new conversations
            intent_result = determine_user_intent(
                goals, user_prompt, [], [], [])
            messages = []
            context = []

            if intent_result.get("new_recommendation_needed", True):
                # Use LLM-detected count if specified, otherwise use default
                recommendation_count = intent_result.get(
                    "requested_perfume_count") or num_recommendations

                recommendations, internal_context, external_context = landing_page_scent_recommendation(
                    recommendation_count, goals, user_prompt, [], mode="dashboard"
                )
                context = internal_context + external_context

                recommendation_summary = generate_recommendation_summary(
                    recommendations, goals, user_prompt, context
                )

                _ = register_external_perfumes_in_shopify(external_context)

                messages = append_message(
                    user_prompt, summary=recommendation_summary, recommendations=recommendations)

                result = db.dashboard_conversations.insert_one({
                    "user_id": user_id,
                    "goals": goals,
                    "messages": messages,
                    "context": context,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })

                return jsonify({
                    "success": True,
                    "mode": "initiate_recommendation",
                    "recommendations": recommendations,
                    "recommendation_summary": recommendation_summary,
                    "context": context,
                    "conversation_id": str(result.inserted_id)
                }), 200

            elif intent_result.get("casual_reply"):
                casual_reply = intent_result["casual_reply"]
                messages = append_message(user_prompt, bot=casual_reply)

                result = db.dashboard_conversations.insert_one({
                    "user_id": user_id,
                    "goals": goals,
                    "messages": messages,
                    "context": [],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })
                return jsonify({
                    "success": True,
                    "mode": "initiate_casual",
                    "casual_reply": casual_reply,
                    "conversation_id": str(result.inserted_id)
                }), 200

            return jsonify({"success": False, "error": "Could not determine user intent."}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/flask/api/home-page-continue-conversation/<string:conversation_id>', methods=['POST'])
def home_page_continue_conversation(conversation_id):
    try:
        if not conversation_id:
            return jsonify({"success": False, "error": "conversation_id is required"}), 400

        conversation = db.home_page_conversation.find_one(
            {"_id": ObjectId(conversation_id)})
        if not conversation:
            return jsonify({"success": False, "error": "Conversation not found"}), 404

        data = request.get_json()
        goals = data.get("goals", conversation.get("goals"))
        user_prompt = data.get("user_prompt")
        selected_perfumes = data.get("selected_perfumes")
        disliked_perfumes = data.get("disliked_perfumes")
        # num_recommendations = random.randint(1, 6)
        num_recommendations = 12

        # Extract stored casual chats if they exist
        casual_conversations = conversation.get("casual_conversations", [])

        # Extract stored perfume-related context
        previous_recommendations = conversation.get("recommendations", [])
        context = conversation.get("context", [])

        # Step 1: Determine User Intent (Casual Chat or Need New Recommendations)
        intent_result = determine_user_intent(
            goals, user_prompt, previous_recommendations, casual_conversations, context
        )

        print(intent_result)  # Debugging statement to check response from LLM
        # liked_perfumes = intent_result.get(
        #     "liked_perfumes", [])  # Get liked perfumes list
        # Check if the user needs a new recommendation
        if intent_result.get("new_recommendation_needed", True):
            # print("disliked_perfumes fff", disliked_perfumes)
            recommendations, internal_context, external_context = landing_page_scent_recommendation(
                num_recommendations, goals, user_prompt, selected_perfumes, disliked_perfumes
            )

            combined_context = internal_context + external_context

            recommendation_summary = generate_recommendation_summary_from_conversation(
                recommendations, goals, user_prompt, combined_context,
                conversation['users_previous_prompts']
            )

            _ = register_external_perfumes_in_shopify(
                external_context)

            # Update MongoDB with new recommendations and summary
            db.home_page_conversation.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        "goals": goals,
                        "recommendations": recommendations,
                        "recommendation_summary": recommendation_summary,
                        "updated_at": datetime.now(),
                        "context": combined_context
                    },
                    "$push": {"users_previous_prompts": user_prompt}
                }
            )

            return jsonify({
                "success": True,
                "recommendations": recommendations,
                "recommendation_summary": recommendation_summary,
                "context": combined_context,
                "conversation_id": str(conversation["_id"])
            }), 200

        # If NOT a recommendation, check for casual chat
        elif intent_result.get("casual_reply"):
            casual_reply = intent_result["casual_reply"]

            # Store casual conversation in DB
            db.home_page_conversation.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$push": {"casual_conversations": {"prompt": user_prompt, "reply": casual_reply}},
                    "$set": {"updated_at": datetime.now()}
                }
            )

            return jsonify({
                "success": True,
                "casual_reply": casual_reply,
                "conversation_id": str(conversation["_id"])
            }), 200

        # Final Fallback: If No Intent Detected, Return Default Response
        return jsonify({
            "success": False,
            "error": "Could not determine user intent."
        }), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/flask/api/dashboard/conversation/<string:user_id>', methods=['GET'])
def get_dashboard_conversation(user_id):
    try:
        conversation = db.dashboard_conversations.find_one(
            {"user_id": user_id})

        if not conversation:
            return jsonify({"success": False, "error": "No conversation found for this user"}), 404

        return jsonify({
            "success": True,
            "conversation_id": str(conversation["_id"]),
            "messages": conversation.get("messages", []),
            "goals": conversation.get("goals", []),
            "context": conversation.get("context", []),
            "created_at": conversation.get("created_at"),
            "updated_at": conversation.get("updated_at")
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/flask/api/change-one-perfume/<string:mode>/<string:id>', methods=['POST'])
def change_one_perfume(mode, id):

    try:
        if not id:
            return jsonify({"success": False, "error": "ID is required"}), 400

        # Map mode to appropriate MongoDB collection
        collection_map = {
            "home": db.home_page_conversation,
            "landing": db.landing_page_prompt
        }

        collection = collection_map.get(mode)
        if collection is None:
            return jsonify({"success": False, "error": "Invalid mode"}), 400

        conversation = collection.find_one({"_id": ObjectId(id)})
        if not conversation:
            return jsonify({"success": False, "error": "Conversation not found"}), 404

        data = request.get_json()
        goals = data.get("goals", conversation.get("goals"))
        user_prompt = data.get("user_prompt")
        selected_perfumes = data.get("selected_perfumes")
        disliked_perfumes = data.get("disliked_perfumes", [])

        recommendations, internal_context, external_context = landing_page_scent_recommendation(
            12, goals, user_prompt, selected_perfumes, disliked_perfumes
        )

        combined_context = internal_context + external_context

        _ = register_external_perfumes_in_shopify(external_context)

        collection.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "recommendations": recommendations,
                    "updated_at": datetime.now(),
                    "context": combined_context
                },
                "$push": {"users_previous_prompts": user_prompt}
            }
        )

        return jsonify({
            "success": True,
            "recommendations": recommendations,
            "_id": str(conversation["_id"])
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# // Product Journal


@app.route('/flask/api/v1/journal', methods=['POST'])
def product_journal():
    journals = db['product_journals']
    data = request.get_json() or {}
    user_id = data.get('userId', '')
    user_name = data.get('userName', '')
    doc_id = data.get('docId')
    messages = data.get('messages')   # list of {role,content} for bootstrap
    single = data.get('message')    # one {role,content} for continuation
    title = data.get('title', '')

    # Get selected and disliked perfumes from frontend if available
    selected_perfumes = data.get('selectedPerfumes', [])
    disliked_perfumes = data.get('dislikedPerfumes', [])
    # print(selected_perfumes, disliked_perfumes)

    # --- NEW JOURNAL BOOTSTRAP ---
    if not doc_id:
        # expecting a messages array
        if not isinstance(messages, list) or not messages:
            return jsonify({'error': 'For new journals you must send a non‑empty "messages" array.'}), 400

        # validate each message
        for m in messages:
            if not isinstance(m, dict) or 'role' not in m or 'content' not in m:
                return jsonify({'error': 'Each entry in "messages" must be an object with "role" and "content".'}), 400

        # insert
        journal = {
            'userId':      user_id,
            'userName':    user_name,
            'journalType': 'Product',
            'title':       title,
            'messages':    messages,
            'selectedPerfumes': selected_perfumes,
            'dislikedPerfumes': disliked_perfumes,
            'createdAt':   datetime.now()
        }
        result = journals.insert_one(journal)
        doc_id = str(result.inserted_id)

    # --- CONTINUE EXISTING JOURNAL ---
    else:
        # validate single message
        if not isinstance(single, dict) or 'role' not in single or 'content' not in single:
            return jsonify({'error': 'Missing or invalid "message" object. Expecting one {role,content}.'}), 400

        # fetch & guard
        try:
            oid = ObjectId(doc_id)
        except:
            return jsonify({'error': 'Invalid docId format.'}), 400

        journal = journals.find_one({'_id': oid})
        if not journal:
            return jsonify({'error': 'Journal not found for this user.'}), 404

        # append the incoming user message
        journals.update_one({'_id': oid}, {'$push': {'messages': single}})
        journal['messages'].append(single)

        # Update title if provided
        if title:
            journals.update_one({'_id': oid}, {'$set': {'title': title}})
            journal['title'] = title

        # Update perfumes lists if provided
        if selected_perfumes:
            journals.update_one(
                {'_id': oid}, {'$set': {'selectedPerfumes': selected_perfumes}})
            journal['selectedPerfumes'] = selected_perfumes
        if disliked_perfumes:
            journals.update_one(
                {'_id': oid}, {'$set': {'dislikedPerfumes': disliked_perfumes}})
            journal['dislikedPerfumes'] = disliked_perfumes

    # --- CALL THE LLM ---
    try:
        response_data = get_journal_response(journal)
        reply = response_data["content"]
        recommend_flag = response_data["recommend_flag"]
    except Exception as e:
        app.logger.error(f"OpenAI error: {e}")
        return jsonify({'error': 'LLM request failed.'}), 500

    # save assistant’s reply
    if recommend_flag:
        assistant_msg = {'role': 'assistant', 'content': response_data.get(
            "recommendation_content", "")}
        journals.update_one({'_id': ObjectId(doc_id)}, {
                            '$push': {'messages': assistant_msg}})
    else:
        assistant_msg = {'role': 'assistant', 'content': reply}
        journals.update_one({'_id': ObjectId(doc_id)}, {
                            '$push': {'messages': assistant_msg}})

    # Prepare the response
    response = {
        'docId': doc_id,
        'reply': reply,
        'title': journal.get('title', ' '),
    }

    # Add recommendation data if needed
    if recommend_flag:
        response.update({
            'showRecommendations': True,
            # 'recommendationContent': response_data.get("recommendation_content", ""),
            'reply': response_data.get("recommendation_content", ""),
            'recommendations': response_data.get("recommendations", []),
        })

    return jsonify(response), 200

# get all journals


@app.route('/flask/api/v1/journal', methods=['GET'])
def get_journal():
    """
    Retrieve both product and life journals.
    Query params:
      - userId: string (required)
      - docId: string (optional)
      - type: string (optional) - 'product', 'life'
    """
    user_id = request.args.get('userId')
    doc_id = request.args.get('docId')
    journal_type = request.args.get('type')  # Optional filter

    if not user_id:
        return jsonify({'error': 'Missing userId query parameter.'}), 400

    # Basic projection for all journals
    projection = {'_id': 1, 'journalType': 1,
                  'summary': 1, 'createdAt': 1, 'journalMode': 1, 'title': 1}

    # Determine collection based on journal type
    if doc_id:
        # Fetch a single journal by ID
        try:
            oid = ObjectId(doc_id)
        except:
            return jsonify({'error': 'Invalid docId format.'}), 400

        # If type is specified, use the appropriate collection
        if journal_type == 'product':
            collection = db['product_journals']
        elif journal_type == 'life':
            collection = db['life_journals']
        else:
            # If no type specified but we have docId, try both collections
            product_doc = db['product_journals'].find_one(
                {'_id': oid, 'userId': user_id})
            life_doc = db['life_journals'].find_one(
                {'_id': oid, 'userId': user_id})

            if product_doc:
                collection = db['product_journals']
            elif life_doc:
                collection = db['life_journals']
            else:
                return jsonify({'error': 'Journal not found.'}), 404

        # Fetch the journal
        doc = collection.find_one({'_id': oid, 'userId': user_id}, projection)
        if not doc:
            return jsonify({'error': 'Journal not found.'}), 404

        # Get messages in a separate query
        full_doc = collection.find_one({'_id': oid}, {'messages': 1})
        messages = full_doc.get('messages', [])

        # Format response
        created_at = doc.get('createdAt', doc['_id'].generation_time)
        resp = {
            'docId': str(doc['_id']),
            'journalType': doc.get('journalType'),
            'createdAt': created_at.isoformat(),
            'messages': messages,
            'title': doc.get('title', '')
        }

        # Add journalMode for Life journals
        if doc.get('journalType') == 'Life':
            resp['journalMode'] = doc.get('journalMode', 'General')

        # Add summary if exists
        if 'summary' in doc and doc['summary'] is not None:
            resp['summary'] = doc['summary']

        return jsonify(resp), 200

    # Fetch all journals for the user
    journals = []

    # If type filter specified, only query that collection
    if journal_type == 'product':
        collections = [('product_journals', 'Product')]
    elif journal_type == 'life':
        collections = [('life_journals', 'Life')]
    else:
        # If no type filter, query both collections
        collections = [('product_journals', 'Product'),
                       ('life_journals', 'Life')]

    for col_name, default_type in collections:
        collection = db[col_name]
        cursor = collection.find(
            {'userId': user_id}, projection).sort('createdAt', -1)

        for doc in cursor:
            created_at = doc.get('createdAt', doc['_id'].generation_time)
            entry = {
                'docId': str(doc['_id']),
                'journalType': doc.get('journalType', default_type),
                'createdAt': created_at.isoformat(),
                'title': doc.get('title', '')
            }

            # Add journalMode for Life journals
            if doc.get('journalType') == 'Life':
                entry['journalMode'] = doc.get('journalMode', 'General')

            # Add summary if exists
            if 'summary' in doc and doc['summary'] is not None:
                entry['summary'] = doc['summary']

            journals.append(entry)

    # Sort all journals by creation date (newest first)
    journals.sort(key=lambda x: x['createdAt'], reverse=True)

    return jsonify({'journals': journals}), 200
# // generate journal summary


@app.route('/flask/api/v1/journal/summary', methods=['POST'])
def generate_journal_summary():
    journals_col = db['product_journals']
    data = request.get_json() or {}
    doc_id = data.get('docId')

    if not doc_id:
        return jsonify({'error': 'Missing docId.'}), 400

    try:
        oid = ObjectId(doc_id)
    except:
        return jsonify({'error': 'Invalid docId format.'}), 400

    # fetch the journal
    journal = journals_col.find_one({'_id': oid})
    if not journal:
        return jsonify({'error': 'Journal not found.'}), 404

    # if we've already generated a summary, just return it
    if 'summary' in journal and journal['summary']:
        return jsonify({
            'docId':  doc_id,
            'summary': journal['summary']
        }), 200

    messages = journal.get('messages', [])
    if not messages:
        return jsonify({'error': 'No messages to summarize.'}), 400

    # generate the summary via LLM
    try:
        summary_obj = get_summary_response(messages)
        print(summary_obj)
    except Exception as e:
        app.logger.error(f"LLM summary error: {e}")
        return jsonify({'error': 'Failed to generate summary.'}), 500

    # save the summary back into the document
    journals_col.update_one(
        {'_id': oid},
        {'$set': {'summary': summary_obj}}
    )

    return jsonify({
        'docId':  doc_id,
        'summary': summary_obj
    }), 200

# life journal


@app.route('/flask/api/v1/life-journal', methods=['POST'])
def life_journal():
    journals = db['life_journals']
    data = request.get_json() or {}
    user_id = data.get('userId', '')
    user_name = data.get('userName', '')
    doc_id = data.get('docId')
    messages = data.get('messages')   # list of {role,content} for bootstrap
    single = data.get('message')    # one {role,content} for continuation
    journal_mode = data.get('journalMode', 'General')
    title = data.get('title', '')

    # --- NEW JOURNAL BOOTSTRAP ---
    if not doc_id:
        # expecting a messages array
        if not isinstance(messages, list) or not messages:
            return jsonify({'error': 'For new journals you must send a non‑empty "messages" array.'}), 400

        # validate each message
        for m in messages:
            if not isinstance(m, dict) or 'role' not in m or 'content' not in m:
                return jsonify({'error': 'Each entry in "messages" must be an object with "role" and "content".'}), 400

        # insert
        journal = {
            'userId':      user_id,
            'userName':    user_name,
            'journalType': 'Life',
            'title':       title,
            'journalMode': journal_mode,
            'messages':    messages,
            'createdAt':   datetime.now()
        }
        result = journals.insert_one(journal)
        doc_id = str(result.inserted_id)

    # --- CONTINUE EXISTING JOURNAL ---
    else:
        # validate single message
        if not isinstance(single, dict) or 'role' not in single or 'content' not in single:
            return jsonify({'error': 'Missing or invalid "message" object. Expecting one {role,content}.'}), 400

        # fetch & guard
        try:
            oid = ObjectId(doc_id)
        except:
            return jsonify({'error': 'Invalid docId format.'}), 400

        journal = journals.find_one({'_id': oid})
        if not journal:
            return jsonify({'error': 'Journal not found for this user.'}), 404

        # append the incoming user message
        journals.update_one({'_id': oid}, {'$push': {'messages': single}})
        journal['messages'].append(single)

        # Update title if provided
        if title:
            journals.update_one({'_id': oid}, {'$set': {'title': title}})
            journal['title'] = title

        # Update journal mode if provided
        if journal_mode and journal_mode != journal.get('journalMode', 'General'):
            journals.update_one(
                {'_id': oid}, {'$set': {'journalMode': journal_mode}})
            journal['journalMode'] = journal_mode

    # --- CALL THE LLM ---
    try:
        response_data = get_life_journal_response(journal)
        reply = response_data["content"]
        generate_summary = response_data.get("generate_summary", False)
    except Exception as e:
        app.logger.error(f"OpenAI error: {e}")
        return jsonify({'error': 'LLM request failed.'}), 500

    # save assistant's reply
    assistant_msg = {'role': 'assistant', 'content': reply}
    journals.update_one({'_id': ObjectId(doc_id)}, {
        '$push': {'messages': assistant_msg}})

    # Generate summary if LLM indicated it's appropriate
    summary = None
    if generate_summary:
        try:
            summary = generate_life_journal_summary(journal)
            # Save summary to database
            journals.update_one({'_id': ObjectId(doc_id)}, {
                '$set': {'summary': summary}})
        except Exception as e:
            app.logger.error(f"Summary generation error: {e}")

    # Prepare the response
    response = {
        'docId': doc_id,
        'title': journal.get('title', ''),
        'reply': reply
    }

    # Include summary if generated
    if summary:
        response['summary'] = summary
        response['showSummary'] = True

    return jsonify(response), 200


@app.route('/flask/api/v1/life-journal/summary', methods=['GET'])
def get_life_journal_summary():
    journals = db['life_journals']
    doc_id = request.args.get('docId')
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'

    if not doc_id:
        return jsonify({'error': 'Missing docId parameter.'}), 400

    # Fetch journal
    try:
        oid = ObjectId(doc_id)
    except:
        return jsonify({'error': 'Invalid docId format.'}), 400

    journal = journals.find_one({'_id': oid})
    if not journal:
        return jsonify({'error': 'Journal not found.'}), 404

    # Check if summary exists and refresh is not forced
    if 'summary' in journal and not force_refresh:
        return jsonify({'summary': journal['summary']}), 200

    # Generate or refresh summary
    try:
        summary = generate_life_journal_summary(journal)
        # Save summary to database
        journals.update_one({'_id': oid}, {'$set': {'summary': summary}})
        return jsonify({'summary': summary}), 200
    except Exception as e:
        app.logger.error(f"Summary generation error: {e}")
        return jsonify({'error': 'Failed to generate summary.'}), 500


@app.route('/flask/api/collection-page-recommend-perfume', methods=['POST'])
def recommend_perfume_collection():
    try:
        data = request.get_json()
        user_prompt = data.get("user_prompt")
        goals = data.get("goals", [])

        recommendations, _, filtered_perfumes_external_context_data = landing_page_scent_recommendation(
            4, goals, user_prompt, [])

        if recommendations == ['Please provide a prompt related to perfumes']:
            return jsonify({
                "success": False,
                "error": "It looks like your prompt isn't related to perfumes. Please provide details about the type of scent you're looking for, and I'd be happy to help!"
            }), 400  # Bad Request

        _ = register_external_perfumes_in_shopify(
            filtered_perfumes_external_context_data)

        return jsonify({"success": True, "recommendations": recommendations}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    response = {
        "error": str(e),
        "message": "An unexpected error occurred."
    }
    return jsonify(response), 500


@app.route('/flask/api/explain-perfume-recommendations', methods=['POST'])
def generate_explanation_of_perfumes():
    """Generates and returns `explanation_of_perfumes` without storing in DB"""
    try:
        data = request.get_json()

        perfume_list = data.get("recommendations")
        goals = data.get("goals", [])
        user_prompt = data.get("user_prompt")
        perfumes_context_data = data.get("context")

        if not perfume_list or not user_prompt:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        explanation = explain_perfume_recommendations(
            perfume_list, goals, user_prompt, perfumes_context_data
        )

        return jsonify({
            "success": True,
            "explanation_of_perfumes": explanation
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
