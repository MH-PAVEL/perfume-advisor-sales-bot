from app.utils.landing_page_ai import client
import json
from datetime import datetime
import app as app

AI_MODEL_TO_USE = "grok-3-mini"


def get_life_journal_response(journal, temperature=0.7, max_tokens=400):
    """
    Generates responses for the Life Journal feature based on the conversation history and journal mode.
    Also determines if a summary should be generated.

    Returns:
        dict: Contains the assistant's response and a flag for summary generation
    """
    messages = journal['messages']
    userName = journal.get('userName', '')
    journalMode = journal.get('journalMode', 'General')

    # Determine the time of day for greeting
    now = datetime.now()
    time_of_day = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"

    system_prompt = f"""
    You are Joy the AI assistant for the {journalMode} Journal feature. Your goal is to have a helpful, supportive conversation with {userName}.
    
    — **Journal Context** —
    - This is a Life Journal in "{journalMode}" mode
    - The user is {userName}
    - It's currently {time_of_day}
    
    — **Your Role Based on Journal Mode** —
    
    If WORK mode:
    • Ask thoughtful follow-up questions about their work challenges, goals, and achievements
    • Help them reflect on productivity, career growth, and work-life balance
    • Offer support for workplace stress and celebrate successes
    
    If HEALTH mode:
    • Discuss physical and mental wellbeing in a supportive way
    • Ask about exercise, nutrition, sleep, or mental health practices
    • Encourage healthy habits without being judgmental
    
    If RELATIONSHIP mode:
    • Help them reflect on personal relationships (family, friends, romantic)
    • Ask thoughtful questions about communication, boundaries, and connection
    • Provide supportive perspective while acknowledging complexity of relationships
    
    If GENERAL mode:
    • Be adaptable to whatever topic the user wishes to discuss
    • Cover a broad range of topics with equal comfort
    • Help the user process thoughts or plan their day
    
    — **Conversation Style** —
    • Be warm, conversational and empathetic
    • Ask follow-up questions that encourage reflection
    • Don't be overly formal or robotic - this is a personal journal
    • Use the user's name occasionally but naturally
    • Keep responses relatively concise (1-3 paragraphs) unless the conversation calls for more depth
    • If the user expresses strong emotions, acknowledge them before moving on
    
    — **Important Guidelines** —
    • Don't repeat the same questions or phrases too frequently
    • Avoid giving prescriptive advice for complex personal issues
    • Never share personal information about the user from previous conversations
    • If the user expresses serious mental health concerns, gently suggest they speak with a professional
    
    — **Summary Generation** —
    When any of these conditions are met, add [SYSTEM:GENERATE_SUMMARY=TRUE] at the end of your response:
    • The conversation has enough depth to create a meaningful summary (typically 4+ exchanges)
    • The user has clearly expressed their mood and its cause
    • The user has discussed specific tasks or action items
    • The user mentions wanting to wrap up or finish the conversation
    • The user explicitly asks for a summary
    
    Do NOT generate a summary if:
    • The conversation is just starting
    • The user is still exploring their thoughts
    • Not enough information has been shared to create a meaningful summary
    
    This is a space for the user to reflect, process thoughts, and engage in helpful conversation.
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

    # Check for summary generation flag
    generate_summary = False
    if "[SYSTEM:GENERATE_SUMMARY=TRUE]" in content:
        generate_summary = True
        # Remove the system marker before sending to user
        content = content.replace("[SYSTEM:GENERATE_SUMMARY=TRUE]", "").strip()

    return {
        "content": content,
        "generate_summary": generate_summary
    }


def generate_life_journal_summary(journal):
    """
    Analyzes the journal conversation and generates a structured summary
    including topic, mood, reason, and tasks.

    Returns:
        dict: A structured summary of the journal
    """
    messages = journal['messages']
    journal_mode = journal.get('journalMode', 'General')
    user_name = journal.get('userName', '')

    # Create prompt for summary generation
    summary_prompt = f"""
    You are an AI assistant that analyzes conversations and extracts key information to create a concise journal summary.
    
    Review the entire conversation between the user ({user_name}) and the assistant about their {journal_mode} journal.
    
    Create a structured summary with the following components:
    
    1. MOOD: Identify the primary emotional state of the user (e.g., Stressed, Happy, Sad, Anxious, Excited, etc.)
    
    2. REASON OF MOOD: Extract the specific cause or trigger for this mood. Be concise but specific (e.g., "Work deadline", "Family issue", "Promotion news")
    
    3. TASKS: Identify 2-4 key actions or tasks that were discussed or should be considered based on the conversation. Format these as brief action items.
    
    Your response should be formatted as a JSON object with these keys. Be concise and accurate, focusing on the most significant information.
    
    Example output format:
    {{
        "mood": "Stressed",
        "reasonOfMood": "Upcoming presentation",
        "tasks": [
            "Prepare slides by Thursday",
            "Practice presentation twice",
            "Email team for feedback"
        ]
    }}
    
    Analyze the conversation thoroughly and provide only the JSON object without any additional text.
    """

    # Prepare conversation for the summary model
    conversation = [
        {"role": "system", "content": summary_prompt},
        *messages
    ]

    # Call the LLM to generate summary
    response = client.chat.completions.create(
        model=AI_MODEL_TO_USE,
        messages=conversation,
        temperature=0.6,
        max_tokens=250
    )

    summary_text = response.choices[0].message.content.strip()

    # Parse the JSON response
    try:
        # Clean up any markdown formatting that might be around the JSON
        cleaned_text = summary_text.replace(
            "```json", "").replace("```", "").strip()
        summary_data = json.loads(cleaned_text)

        # Add the journal topic from the journal mode
        summary_data["journalTopic"] = journal_mode

        return summary_data
    except json.JSONDecodeError as e:
        # If JSON parsing fails, create a basic structure with the error
        app.logger.error(f"Failed to parse summary JSON: {e}")
        return {
            "journalTopic": journal_mode,
            "mood": "Unknown",
            "reasonOfMood": "Could not determine",
            "tasks": ["Review journal content"]
        }
