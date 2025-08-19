# from app.utils.functions import query_pinecone,query_pinecone_for_external_data,llm,llmSecondary


# def generate_response(user_input,chat_history,user_context):

#     # Construct prompt for refining the query
#     refine_prompt = (
#         "You are an AI assistant specializing in refining user queries based on previous conversation context. "
#         "If there are perfume names present in the users last query and the user is asking explanation for the suggestion keep those perfume names definitely in the refined query."
#         "Your goal is to take the current chat history,user context,weather update and user input, then refine the user's query to make it clearer and more specific. "
#         "If the user is asking recommedations for someone else (ex: brother,sister, boyfriend, girlfriend etc.), then don't assume her details for the other persons details.If the user doesn't mentiones for whom asking the recommedations then assume its for them."
#         "If the query is already clear, return it as is.\n\n"
#         "Just provide the refined query, don't add unnecessary sentences."
#         "It's winter in United Kingdom of Great Britain and Northern Ireland"
#         "add the weather info also in the refined query"
#         f"{user_context}\n\n"
#         f"Current User Chat History:\n{chat_history}\n\n"
#         f"Current User Query: {user_input}\n\n"
#         "Refined Query:"
#     )

#     # print("refined prompt", refine_prompt)
#     # Construct prompt for generating chat summary
#     summary_prompt = (
#         "You are an AI assistant tasked with summarizing the conversation between the user and the AI assistant. "
#         "Your goal is to create a concise and clear summary of the chat history, highlighting the key points, user preferences, and any specific requests or recommendations made. "
#         "Focus on capturing the essence of the conversation, including any perfume recommendations, user details, and contextual information like weather or events. "
#         "Ensure the summary is brief yet comprehensive enough to provide context for future interactions.\n\n"
#         f"Chat History:\n{chat_history}\n\n"
#         "Summary:"
#     )

#     # Generate the chat summary using llmForRefiningQuery
#     chat_summary = llmSecondary.invoke(summary_prompt).content
#     refined_query = llmSecondary.invoke(refine_prompt).content
#     # print("refined Query: ", refined_query.content)
#     # Retrieve relevant documents from Pinecone
#     retrieval_results = query_pinecone(refined_query)
#     retrieval_results_external = query_pinecone_for_external_data(refined_query)
#     # print("context:", retrieval_results_external)
#     # Prepare context from the retrieved documents
#     context = "\n".join([match['metadata']['name'] + ": " + match['metadata']['text']
#                         for match in retrieval_results.matches])

#     contextOfExternalPerfumes = "\n".join([match['metadata']['description']
#                                            for match in retrieval_results_external.matches])
#     # print("context:", contextOfExternalPerfumes)

#     # # Construct the LLM prompt
#     prompt = (
#         "You are Joy, an AI assistant specializing in perfumes, and you work for Evoked. "
#         "Evoked is a perfume brand for which you are working as an AI assistant to help users find their ideal perfumes. "
#         "You answer questions about specific perfumes and, if the query is unrelated to perfumes, converse with the user like a normal human being. "
#         "Your tone should be friendly, professional, and engaging.\n\n"
#         "User details to know whom you are talking to:\n"
#         f"{user_context}\n\n"
#         "Current Weather update:\n"
#         "It's winter in United Kingdom of Great Britain and Northern Ireland\n\n"
#         "Retrieved Context Of Evoked Perfume regarding user's query:\n"
#         f"{context}\n\n"
#         "Retrieved Context of External Perfumes:\n"
#         f"{contextOfExternalPerfumes}\n\n"
#         "from the context data of both Evoked and external perfumes, suggest the best 3 perfumes for the user depending on their details, weather of their location, any specific events they mention, and the chat history.\n"
#         "Previous chat summery: \n"
#         f"{chat_summary}\n"
#         f"User Query: {user_input}\n\n"
#         "Use the user's stated interest (Evoked perfumes, external perfumes, or both) to determine the focus of your recommendations. If unclear, clarify before proceeding."
#         "Provide a detailed and helpful response in Markdown Format tailored to the user's context, chat summary, retrieved context of both Evoked and external perfumes, and query, while following the instructions."
#         "Instructions for the assistant:\n"
#         "1. If the user's query is specifically about Evoked's perfume collection:"
#         "   - Use the retrieved context for Evoked perfumes to craft a detailed and accurate response."
#         "   - Pick the top 3 perfumes from Evoked depending on the user's details, weather, chat history, and any specific events they mention."
#         "2. If the user's query is specifically about external perfumes (other brands):\n"
#         "   - Use the retrieved context for external perfumes to suggest the best 3 perfumes.\n"
#         "   - Base recommendations on the user's details, weather, chat history, and any specific events they mention.\n"
#         "   - If the retrieved context of external perfumes is irrelevant, acknowledge it and provide general insights about perfumes. Avoid making irrelevant recommendations.\n\n"
#         "3. If the user is interested in both Evoked and external perfumes: (if the user doesn't mentions in which he is in interesred then think he is interested in both)\n"
#         "   - Use the retrieved context of both Evoked and external perfumes.\n"
#         "   - Suggest the top 5 perfumes(3 from evoked,2 from external), including a mix from both Evoked and external brands if appropriate, based on the user's details, weather, and specific preferences.\n\n"
#         "4. If the user expresses interest in a perfume from the external context:\n"
#         "   - Provide detailed information about the perfume, including its notes (top, middle, base) and main accords, based on the retrieved context.\n"
#         "   - Offer the option to create a custom perfume inspired by that perfume's ingredients.\n"
#         "   - Highlight that the custom perfume can use similar top notes, middle notes, and base notes tailored to the user's preferences.\n"
#         "   - Use engaging and professional language to explain how the custom perfume process works and how it can be personalized to the user's liking.\n\n"
#         """ - After describing the external perfume, include a suggestion like:\n
#         "If you're interested, we can create a custom perfume inspired by this fragrance, using similar top, middle, and base notes to craft a scent uniquely tailored to you."\n
#             - If the user asks for details, provide an overview of the customization process, such as selecting specific notes, choosing intensity, and adding any personal preferences.\n
#         """
#         """ - Ensure the custom perfume option is presented politely as a choice, not a requirement. For example:\n
#         "This is a great fragrance! If you'd like, we can create a custom perfume inspired by it using similar ingredients to suit your personal preferences."\n
#         """
#         "4. If the query is about external perfumes but the retrieved context is irrelevant, acknowledge the query and provide general insights. Future updates will enable more precise answers.\n"
#         "5. If the query is unrelated to perfumes, rely on your general knowledge to provide a helpful and conversational response.\n"
#         "6. Always prioritize the retrieved context of Evoked perfumes when answering questions specifically about Evoked's collection.\n"
#         "7. Maintain a concise and helpful tone, ensuring the response is tailored to the user's query and context.\n"
#         "8. If the user's interest is unclear, politely ask for clarification before proceeding with your response.\n"
#         "9. Focus your response on the specific query provided by the user. If the user mentions a specific perfume (e.g., 'Alchemy'), provide detailed information only about that perfume unless the user asks for comparisons or other recommendations.\n"
#         "10. Use the user context only if it directly enhances the response. Avoid repeating it unnecessarily unless it adds value to the answer.\n"
#         "11. If the user's query is unclear or incomplete, politely ask for clarification before proceeding with your response.\n\n"
#         "12. If the retrieved context is irrelevant to the user's query: \n"
#         "    - Acknowledge that the context doesn't match the query.\n"
#         "    - Provide a helpful and relevant response based on your general knowledge.\n"
#         "    - Avoid referencing the retrieved context unless it directly addresses the user's question.\n\n"
#         "13. If the user is asking recommendations for someone else (e.g., brother, sister, boyfriend, girlfriend, etc.), ask follow-up questions to know about the person for whom you will recommend.\n"
#         "14. Avoid recalling user details too much in the conversation, as it may feel unnatural. Refer to the chat history to decide if a greeting or recall is necessary.\n"
#         "15. Mention previous conversations only if necessary for context. Avoid referencing them otherwise.\n"
#         "16. Limit congratulatory or repetitive statements, say Hello only if the user says hello to you.\n"
#         "17. Avoid using phrases like 'Considering your fondness for X vibes.' Use alternatives like, 'Based on your preferences, I recommend…'\n"
#         "18. Always aim for concise and clear follow-ups or subsequent recommendations.\n"
#         "19. Do not repeatedly mention the same details unless it directly adds value to the conversation.\n"
#         "20. When discussing weather, user preferences, or events, mention them naturally and only when relevant to the recommendation.\n"
#         "21. Provide recommendations based on the user's details, weather, and chat history while avoiding unnecessary repetition or irrelevant information.\n\n"
#         # "22. If user is more liking t"

#     )

#     response = llm.invoke(prompt)

#     return response.content  # Change this line to access the content attribute
