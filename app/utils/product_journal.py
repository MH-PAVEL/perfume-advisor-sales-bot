from app.utils.landing_page_ai import client
import json
import re
from app.utils.landing_page_ai import landing_page_scent_recommendation

AI_MODEL_TO_USE = "grok-3-mini"


def get_journal_response(journal, temperature=0.8, max_tokens=800):
    """
    Calls OpenAI ChatCompletion with full message history.
    """
    messages = journal['messages']
    userName = journal['userName']
    selected_perfumes = journal.get('selectedPerfumes', [])
    disliked_perfumes = journal.get('dislikedPerfumes', [])

    # print(selected_perfumes, disliked_perfumes, "from journal")
    system_prompt = f"""
                You are ScentGPT, a friendly fragrance-logging assistant with a warm, conversational tone. The front end will always send the user's answers about their scents and experiences; engage with that information naturally.

                — **Context & Flow** —
                1. User has already shared: scent names, where they wore them, and how they felt
                2. Detect sentiment from their feedback and personalize your approach
                3. If user mentions anything off-topic, respond to it naturally first, then transition back to the appropriate question

                — **Sentiment Paths** —
                For POSITIVE sentiment (user seems happy with their scents):
                • First ask (vary wording): "What occasion did you wear [scents] to?"
                • Then ask (vary wording): "Did anyone comment or notice your fragrance?"
                • Finally ask (vary wording): "Would you like to save these to your collection with any special labels?"
                • After labeling, respond: "That's all set for you, {userName}! Enjoy your day 😊" and mark session COMPLETED.

                For NEGATIVE sentiment (user isn't satisfied with scents):
                • Acknowledge their feedback with empathy
                • Ask what specifically didn't work (notes, longevity, etc.)
                • After they respond, say: "Thanks for sharing. I'll find something better suited for you! Let me prepare some recommendations..."
                • IMPORTANT: Include exactly this marker at the END of your message: [SYSTEM:RECOMMEND=TRUE]
                • IMPORTANT: If you include the recommendation marker, ALSO include a second & third marker with the search query and perfume no for new fragrances:
                    [SYSTEM:QUERY=insert detailed search query based on user preferences here]
                    The query should capture:
                    - Preferred notes (e.g., more fruity, less spicy)
                    - Desired characteristics (e.g., longer lasting, better projection)
                    - Any specific use cases (e.g., daily wear, special occasions)
                    [SYSTEM:PERFUME_NO=Give the number of perfumes user used in the journal here]


                • Don't actually make recommendations yourself - the system will handle this

                — **Conversation Style** —
                • Sound natural and friendly, not scripted
                • Vary your phrasing for questions (don't use identical wording each time)
                • Use relevant emojis occasionally but not excessively
                • Keep responses brief and conversational
                • Remember user's previous answers and reference them

                Always respond to what the user actually says, and if they mention something important (like their wife's preferences), acknowledge it before continuing with your next question.
                """
    # Prepend system role
    system = {
        'role': 'system',
        'content': system_prompt
    }
    conversation = [system] + messages
    response = client.chat.completions.create(
        model=AI_MODEL_TO_USE,
        messages=conversation,
        temperature=temperature,
        max_tokens=max_tokens
    )
    content = response.choices[0].message.content.strip()
    print(content)
    # Check for recommendation flag
    recommend_flag = False
    if "[SYSTEM:RECOMMEND=TRUE]" in content:
        recommend_flag = True
        # Extract the search query
        query_match = re.search(r'\[SYSTEM:QUERY=(.*?)\]', content)
        if query_match:
            user_query = query_match.group(1).strip()

        # Extract the perfume number
        perfume_no_match = re.search(r'\[SYSTEM:PERFUME_NO=(\d+)\]', content)
        if perfume_no_match:
            try:
                perfume_no = int(perfume_no_match.group(1))
            except ValueError:
                # Fallback to default if parsing fails
                perfume_no = 2

        # Remove the markers from the content
        content = re.sub(r'\[SYSTEM:[^\]]+\]', '', content).strip()
        # Calling perfume recommendation function
        recommendations, internal_context, external_context = landing_page_scent_recommendation(
            perfume_no=perfume_no,
            goals=["smell unique", "boost confidence",
                   "improve mood", "increase attraction"],
            user_prompt=user_query,
            selected_perfumes=selected_perfumes,
            disliked_perfumes=disliked_perfumes,
            mode="dashboard"
        )

        # Format the recommendations into a presentable response
        rec_prompt = f"""
        You are ScentGPT, a fragrance expert. Based on the user's feedback about their previous scents,
        you're suggesting these alternatives that better match their preferences:
        
        {recommendations}
        
        Internal context for these fragrances:
        {internal_context}
        
        External context for these fragrances:
        {external_context}

        requested perfumes to replace : {disliked_perfumes}, use these names to use in the part where you need to mention which perfume is replaced with which one (make this part bold as well).
        
        Create a friendly response introducing these alternatives that looks like this example:

        "I hear you, {userName}. Let's get these sorted. Based on what you've shared, I believe replacing X would be a better fit for the upcoming month. Would you like to replace the previous ones with options that would be better for you.

        1. ASTRALIS ✅ [Replaced with Obsidian!]
        • Notes: Bergamot, Black Currant, Apple, Vanilla, Cedar
        • Feel: Boldly conquering the world.
        • Best for: Daily Workwear, Post Workout, and more.

        2. SUCCEXA ✅ [Replaced with Kalone!]
        • Notes: Bergamot, Red Rose, Sandalwood, Musk
        • Feel: A serene sunset over golden dunes.
        • Best for: Daily Workwear, Black Ties."
        
        Format it in a clean, easy-to-read way as shown above. Maintain the numbering style, bullet points, and clear sections for each fragrance.
        
        DON'T include markdown formatting or system tags in your response.
        """

        format_response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": rec_prompt}],
            temperature=0.7,
            max_tokens=700
        )

        recommendation_content = format_response.choices[0].message.content.strip(
        )
        return {
            "content": content,
            "recommend_flag": recommend_flag,
            "recommendations": recommendations,
            "recommendation_content": recommendation_content,
            "perfume_no": perfume_no
        }

    # If no recommendations needed
    return {
        "content": content,
        "recommend_flag": recommend_flag
    }


def get_summary_response(messages):
    """
    Ask the LLM to produce a JSON summary with these fields:
      - scentsUsed: [string]
      - mood: string
      - scentUsedPlaces: [{ scent: string, place: string }]
      - labels: [{ scent: string, label: string }]
    Returns a Python dict.
    """
    system = {
        "role": "system",
        "content": """
        You are ScentGPT. Given a 'messages' array of a completed, positive-flow fragrance journal, output exactly one JSON object with:
        • title: the title of the journal
        • scentsUsed: array of scent names
        • mood: the single dominant emotion (string)
        • scentUsedPlaces: array of objects { "scent": ..., "place": ... }
        • labels: array of objects { "scent": ..., "label": ... }
        Respond with JSON only, no extra text.
        """
    }
    user = {
        "role": "user",
        "content": json.dumps({"messages": messages})
    }

    resp = client.chat.completions.create(
        model=AI_MODEL_TO_USE,
        messages=[system, user],
        temperature=0
    )
    text = resp.choices[0].message.content

    # parse JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # optionally log the raw 'text' for debugging
        raise RuntimeError(f"Invalid JSON from LLM: {text}") from e
