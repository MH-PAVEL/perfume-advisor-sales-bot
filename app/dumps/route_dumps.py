
# perfume = [{'id': '1', 'title': 'Whiskey Woods', 'description': 'Whiskey Woods is a captivating Oriental Woody fragrance that immerses you in the essence of smoky sophistication. The fragrance opens with bold top notes of tobacco and whiskey, evoking a warm, inviting narrative. As it develops, the heart reveals rich notes of labdanum, amber, and cinnamon, wrapping you in a comforting embrace. The base features a robust blend of incense, cedar, and oakmoss, anchoring the scent in earthy elegance. This fragrance is designed for those who appreciate depth and complexity, perfect for sophisticated evenings or intimate gatherings.',
#             'feels_like': 'Smoky sophistication', 'primary_scent_goal': ['smell unique'], 'secondary_scent_goal': ['boost confidence'], 'occasions': ['Formal events', 'Evening outings', 'Candlelit dinners'], 'scent_family': ['Oriental', 'Woody'], 'seasons': ['Fall', 'Winter'], 'target_gender': ['Unisex'], 'scent_vibes': ['Warm', 'Smoky', 'Balsamic'], 'top_notes': ['Tobacco', 'Whiskey'], 'middle_notes': ['Labdanum', 'Amber', 'Cinnamon'], 'bottom_notes': ['Incense', 'Cedar', 'Oakmoss']}]
# perfume_data = [
#     {
#         "id": "18448",
#         "title": "Elysian Plum Embrace",
#         "description": "Elysian Plum Embrace is an exquisite Oriental Woody fragrance crafted for the discerning gentleman...",
#         "feels_like": "Elegant and inviting",
#         "primary_scent_goal": ["smell unique"],
#         "secondary_scent_goal": ["improve mood"],
#         "occasions": ["Evening events", "Date nights", "Special occasions"],
#         "scent_family": ["Oriental", "Woody"],
#         "seasons": ["Autumn", "Winter"],
#         "target_gender": ["Male"],
#         "scent_vibes": ["Warm", "Spicy", "Fruity"],
#         "top_notes": ["Plum", "Chutney", "Italian Lemon", "Clove"],
#         "middle_notes": ["Lavender", "Clary Sage"],
#         "bottom_notes": ["Vanilla", "Nutmeg", "Patchouli"]
#     }
# ]


# @app.route('/api/create-conversation', methods=['POST'])
# def create_conversation():
#     # Get the JSON data from the request
#     data = request.get_json()

#     # Validate the required fields
#     if not data or 'user_id' not in data or 'user_context' not in data or 'user_input' not in data:
#         return jsonify({"error": "Missing required fields: user_id, user_context, or user_input"}), 400

#     # Extract the fields
#     user_id = data['user_id']
#     user_context = data['user_context']
#     user_input = data['user_input']
#     chat_history = [{"role": "AI assistant JOY",
#                      "content": "Hello! I'm Joy, your AI assistant. How can I assist you today?"}]

#     # Validate the structure of user_context (optional but recommended)
#     if not isinstance(user_context, dict):
#         return jsonify({"error": "user_context must be a dictionary/object"}), 400

#     chat_history.append({"role": "user", "content": user_input})
#     response = generate_response(user_input, chat_history, user_context)
#     chat_history.append({"role": "AI assistant JOY", "content": response})

#     # Create a document to save in MongoDB
#     conversation_data = {
#         "user_id": user_id,
#         "user_context": user_context,  # Save the entire user_context object
#         "user_input": user_input,
#         "chat_history": chat_history,
#         "response": response,
#         "timestamp": datetime.utcnow()  # Use datetime.datetime for the timestamp
#     }

#     # Insert the document into the 'conversation' collection
#     result = db.conversation.insert_one(conversation_data)

#     # Add the inserted ID to the response data (optional)
#     conversation_data["_id"] = str(result.inserted_id)

#     # Return a success response
#     return jsonify({"message": "Conversation created successfully", "data": conversation_data}), 201


# @app.route('/api/continue-conversation', methods=['POST'])
# def continue_conversation():
#     # Get the JSON data from the request
#     data = request.get_json()

#     # Validate the required fields
#     if not data or 'conversation_id' not in data or 'user_input' not in data:
#         return jsonify({"error": "Missing required fields: conversation_id or user_input"}), 400

#     # Extract the fields
#     conversation_id = data['conversation_id']
#     user_input = data['user_input']

#     try:
#         # Convert conversation_id to ObjectId
#         object_id = ObjectId(conversation_id)
#     except Exception as e:
#         return jsonify({"error": "Invalid conversation_id"}), 400

#     # Find the existing conversation in MongoDB
#     existing_conversation = db.conversation.find_one({"_id": object_id})

#     # Check if the conversation exists
#     if not existing_conversation:
#         return jsonify({"error": "Conversation not found"}), 404

#     # Extract user_context and chat_history from the existing conversation
#     user_context = existing_conversation.get("user_context", {})
#     chat_history = existing_conversation.get("chat_history", [])

#     print(user_context)
#     print(chat_history)
#     # Generate a response using the imported function
#     generated_response = generate_response(
#         user_input, chat_history, user_context)

#     # Append the new user input and generated response to the chat history
#     chat_history.append({"role": "user", "content": user_input})
#     chat_history.append(
#         {"role": "AI assistant", "content": generated_response})

#     # Update the existing conversation in MongoDB
#     db.conversation.update_one(
#         {"_id": object_id},  # Filter by _id
#         {
#             "$set": {
#                 "user_input": user_input,  # Update the latest user input
#                 "response": generated_response,  # Update the latest response
#                 "chat_history": chat_history,  # Update the chat history
#                 "timestamp": datetime.utcnow()  # Update the timestamp
#             }
#         }
#     )

#     # Fetch the updated conversation
#     updated_conversation = db.conversation.find_one(
#         {"_id": object_id}, {"_id": 0})  # Exclude _id from the response

#     # Return a success response
#     return jsonify({"message": "Conversation continued successfully", "data": updated_conversation}), 200


# @app.route('/api/data', methods=['GET'])
# def get_data():
#     # Retrieve all documents from the collection
#     documents = list(db.mycollection.find({}, {'_id': 0}))
#     return jsonify(documents), 200


# @app.route('/api/conversations', methods=['GET'])
# def conversations():
#     # Get JSON data from the request body
#     data = request.get_json()

#     # Validate the required fields
#     if not data or 'user_id' not in data or 'mode' not in data:
#         return jsonify({"error": "Missing required fields: user_id or mode"}), 400

#     # Extract the fields
#     user_id = data['user_id']
#     mode = data['mode']

#     try:
#         # Fetch conversations from MongoDB filtered by user_id and mode
#         conversations = list(db.conversation.find(
#             # Filter by user_id and mode inside user_context
#             {"user_id": user_id, "user_context.mode": mode},
#             # Exclude the _id field from the response
#             {"_id": 1, "user_id": 1, "user_context": 1, "chat_history": 1}
#         ))

#         for conversation in conversations:
#             conversation["_id"] = str(conversation["_id"])
#         # Check if any conversations were found
#         if not conversations:
#             return jsonify({"message": "No conversations found for the given user_id and mode", "data": []}), 200

#         # Return the filtered conversations
#         return jsonify({"message": "Conversations searched successfully", "data": conversations}), 200

#     except Exception as e:
#         return jsonify({"error": f"An error occurred: {str(e)}"}), 500


#
# @app.route('/api/delete-conversation', methods=['DELETE'])
# def delete_conversation():
#     # Get the JSON data from the request
#     data = request.get_json()
#
#     # Validate the required fields
#     if not data or 'user_id' not in data or 'conversation_id' not in data:
#         return jsonify({"error": "Missing required fields: user_id or conversation_id"}), 400
#
#     # Extract the fields
#     user_id = data['user_id']
#     conversation_id = data['conversation_id']
#
#     try:
#         # Convert conversation_id to ObjectId
#         object_id = ObjectId(conversation_id)
#     except Exception as e:
#         return jsonify({"error": "Invalid conversation_id"}), 400
#
#     # Delete the conversation if it matches both user_id and conversation_id
#     result = db.conversation.delete_one({"_id": object_id, "user_id": user_id})
#     print(result,"result")
#     #Check if the conversation was deleted
#     if result.deleted_count == 1:
#         return jsonify({"message": "Conversation deleted successfully"}), 200
#     else:
#         return jsonify({"error": "Conversation not found or does not belong to the user"}), 404


# @app.route('/api/delete-conversation', methods=['DELETE'])
# def delete_conversation():
#     # Get the JSON data from the request
#     data = request.get_json()

#     # Validate the required fields
#     if not data or 'user_id' not in data or 'conversation_id' not in data:
#         return jsonify({"error": "Missing required fields: user_id or conversation_id"}), 400

#     # Extract the fields
#     user_id = data['user_id']
#     conversation_id = data['conversation_id']
#     mode = data['mode']
#     try:
#         # Convert conversation_id to ObjectId
#         object_id = ObjectId(conversation_id)
#     except Exception as e:
#         return jsonify({"error": "Invalid conversation_id"}), 400

#     # Delete the conversation if it matches both user_id and conversation_id
#     result = db.conversation.delete_one({"_id": object_id, "user_id": user_id})

#     # Check if the conversation was deleted
#     if result.deleted_count == 1:
#         # Fetch the remaining conversations for the user
#         remaining_conversations = list(db.conversation.find(
#             {"user_id": user_id, "user_context.mode": mode},  # Filter by user_id
#             # Include only necessary fields
#             {"_id": 1, "user_id": 1, "user_context": 1, "chat_history": 1}
#         ))

#         # Convert ObjectId to string for JSON serialization
#         for conversation in remaining_conversations:
#             conversation["_id"] = str(conversation["_id"])

#         # Return success response with remaining conversations
#         return jsonify({
#             "message": "Conversation deleted successfully",
#             "remaining_conversations": remaining_conversations
#         }), 200
#     else:
#         return jsonify({"error": "Conversation not found or does not belong to the user"}), 404


# @app.route('/api/anonymous/create-conversation', methods=['POST'])
# def create_anonymous_conversation():
#     # Get the JSON data from the request
#     data = request.get_json()

#     # Validate the required field
#     if not data or 'user_input' not in data:
#         return jsonify({"error": "Missing required field: user_input"}), 400

#     # Extract the user input
#     user_input = data['user_input']

#     # Initialize the chat history with a default AI message
#     chat_history = [{"role": "AI assistant JOY",
#                      "content": "Hello! I'm Joy, your AI assistant. How can I assist you today?"}]

#     # Append the user's input to the chat history
#     chat_history.append({"role": "user", "content": user_input})

#     # Generate a response using the imported function
#     response = anonymous_generate_response(user_input, chat_history)
#     # print(response["response"], "response")
#     # Append the AI's response to the chat history
#     chat_history.append({"role": "AI assistant JOY",
#                         "content": response["response"]})

#     # Create a document to save in MongoDB
#     conversation_data = {
#         "chat_history": chat_history,
#         "timestamp": datetime.utcnow()  # Use datetime.datetime for the timestamp
#     }

#     # Insert the document into the 'anonymous_conversations' collection
#     result = db.anonymous_conversations.insert_one(conversation_data)

#     # Prepare the response data
#     response_data = {
#         "conversation_id": str(result.inserted_id),
#         "chat_history": chat_history,
#         "perfumes": response["context"],
#         "response": response["response"],
#         "timestamp": conversation_data["timestamp"],
#     }

#     # Return a success response
#     return jsonify({"message": "Conversation created successfully", "data": response_data}), 201


# @app.route('/api/anonymous/continue-conversation', methods=['POST'])
# def continue_anonymous_conversation():
#     # Get the JSON data from the request
#     data = request.get_json()

#     # Validate the required fields
#     if not data or 'conversation_id' not in data or 'user_input' not in data:
#         return jsonify({"error": "Missing required fields: conversation_id or user_input"}), 400

#     # Extract the fields
#     conversation_id = data['conversation_id']
#     user_input = data['user_input']

#     try:
#         # Convert conversation_id to ObjectId
#         object_id = ObjectId(conversation_id)
#     except Exception as e:
#         return jsonify({"error": "Invalid conversation_id"}), 400

#     # Find the existing conversation in MongoDB
#     existing_conversation = db.anonymous_conversations.find_one(
#         {"_id": object_id})

#     # Check if the conversation exists
#     if not existing_conversation:
#         return jsonify({"error": "Conversation not found"}), 404

#     # Extract the chat history from the existing conversation
#     chat_history = existing_conversation.get("chat_history", [])

#     # Append the new user input to the chat history
#     chat_history.append({"role": "user", "content": user_input})

#     # Generate a response using the imported function
#     response = anonymous_generate_response(user_input, chat_history)

#     # Append the AI's response to the chat history
#     chat_history.append({"role": "AI assistant JOY",
#                         "content": response["response"]})

#     # Update the existing conversation in MongoDB
#     db.anonymous_conversations.update_one(
#         {"_id": object_id},  # Filter by _id
#         {
#             "$set": {
#                 "chat_history": chat_history,  # Update the chat history
#                 "timestamp": datetime.utcnow()  # Update the timestamp
#             }
#         }
#     )

#     # Prepare the response data
#     response_data = {
#         "conversation_id": conversation_id,
#         "chat_history": chat_history,
#         "perfumes": response["context"],
#         "response": response["response"],
#         "timestamp": datetime.utcnow()
#     }

#     # Return a success response
#     return jsonify({"message": "Conversation continued successfully", "data": response_data}), 200


# @app.route('/flask/api/home-page-continue-conversation/<string:conversation_id>', methods=['POST'])
# def home_page_continue_conversation(conversation_id):
#     try:
#         if not conversation_id:
#             return jsonify({"success": False, "error": "conversation_id is required"}), 400

#         conversation = db.home_page_conversation.find_one(
#             {"_id": ObjectId(conversation_id)})
#         if not conversation:
#             return jsonify({"success": False, "error": "Conversation not found"}), 404

#         data = request.get_json()
#         goals = data.get("goals", conversation.get("goals"))
#         user_prompt = data.get("user_prompt")

#         # Extract stored casual chats if they exist
#         casual_conversations = conversation.get("casual_conversations", [])

#         # Extract stored perfume-related context
#         previous_recommendations = conversation.get("recommendations", [])
#         context = conversation.get("context", [])

#         # Step 1: Determine User Intent (Casual Chat or Need New Recommendations)
#         intent_result = determine_user_intent(
#             goals, user_prompt, previous_recommendations, casual_conversations, context)
#         print(intent_result)
#         # LLM determined this is a casual chat
#         if intent_result.get("new_recommendation_needed", False):
#             casual_reply = intent_result["casual_reply"]

#             # Store in conversation history for future chat context
#             db.home_page_conversation.update_one(
#                 {"_id": ObjectId(conversation_id)},
#                 {
#                     "$push": {"casual_conversations": {"prompt": user_prompt, "reply": casual_reply}},
#                     "$set": {"updated_at": datetime.now()}
#                 }
#             )

#             return jsonify({
#                 "success": True,
#                 "casual_reply": casual_reply,
#                 "conversation_id": str(conversation["_id"])
#             }), 200

#         # User wants new recommendations
#         elif intent_result.get("new_recommendation_needed", True):
#             recommendations, internal_context, external_context = landing_page_scent_recommendation(
#                 12, goals, user_prompt, []
#             )

#             combined_context = internal_context + external_context

#             recommendation_summary = generate_recommendation_summary_from_conversation(
#                 recommendations, goals, user_prompt, combined_context,
#                 conversation['users_previous_prompts']
#             )

#             # Update MongoDB with new recommendations
#             db.home_page_conversation.update_one(
#                 {"_id": ObjectId(conversation_id)},
#                 {
#                     "$set": {
#                         "goals": goals,
#                         "recommendations": recommendations,
#                         "recommendation_summary": recommendation_summary,
#                         "updated_at": datetime.now(),
#                         "context": combined_context
#                     },
#                     "$push": {
#                         "users_previous_prompts": user_prompt
#                     }
#                 }
#             )

#             return jsonify({
#                 "success": True,
#                 "recommendations": recommendations,
#                 "recommendation_summary": recommendation_summary,
#                 "context": combined_context,
#                 "conversation_id": str(conversation["_id"])
#             }), 200

#     except Exception as e:
#         return jsonify({"success": False, "error": str(e)}), 500


# @app.route('/flask/api/home-page-continue-conversation/<string:conversation_id>', methods=['POST'])
# def home_page_continue_conversation(conversation_id):
#     try:
#         if not conversation_id:
#             return jsonify({"success": False, "error": "conversation_id is required"}), 400

#         # Fetch existing conversation
#         conversation = db.home_page_conversation.find_one(
#             {"_id": ObjectId(conversation_id)})
#         if not conversation:
#             return jsonify({"success": False, "error": "Conversation not found"}), 404
#         print(conversation)
#         # Get request data
#         data = request.get_json()
#         goals = data.get("goals")
#         user_prompt = data.get("user_prompt")

#         # Get new recommendations
#         recommendations, filtered_perfumes_internal_context_data, filtered_perfumes_external_context_data = landing_page_scent_recommendation(
#             12, goals, user_prompt, [])

#         # Generate `recommendation_summary`
#         recommendation_summary = generate_recommendation_summary_from_conversation(
#             recommendations, goals, user_prompt,
#             filtered_perfumes_internal_context_data +
#             filtered_perfumes_external_context_data,
#             conversation['users_previous_prompts']
#         )
#         # Update MongoDB with new recommendations and summary immediately
#         db.home_page_conversation.update_one(
#             {"_id": ObjectId(conversation_id)},
#             {
#                 "$set": {
#                     "goals": goals,
#                     "recommendations": recommendations,
#                     "recommendation_summary": recommendation_summary,
#                     "updated_at": datetime.now()
#                 },
#                 "$push": {
#                     "users_previous_prompts": user_prompt
#                 }
#             }
#         )

#         # # Start background processing for Shopify & Pinecone
#         # threading.Thread(
#         #     target=background_processing_for_home_page,
#         #     args=(filtered_perfumes_external_context_data,)
#         # ).start()

#         # Send immediate response
#         return jsonify({
#             "success": True,
#             "recommendations": recommendations,
#             "recommendation_summary": recommendation_summary,
#             "context": filtered_perfumes_internal_context_data + filtered_perfumes_external_context_data,
#             "conversation_id": str(conversation["_id"])
#         }), 200

#     except Exception as e:
#         return jsonify({"success": False, "error": str(e)}), 500
