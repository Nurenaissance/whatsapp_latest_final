
import os
import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from openai import OpenAI
from .models import Conversation, SentimentAnalysis
from django.http import JsonResponse, HttpResponseBadRequest
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404

# Define the OpenAI sentiment analysis function
# Set up your OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_sentiment(text):
    """Analyze sentiment of the given text using OpenAI GPT."""
    try:
        # Define the chunk size (max 4000 characters)
        chunk_size = 4000
        sentiment_results = []

        # Split the text into chunks if it's longer than chunk_size
        text_chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

        for chunk in text_chunks:
            # Define the prompt for sentiment analysis
            sentiment_prompt = f"""
            Please analyze the following WhatsApp conversation and provide sentiment analysis based on the user's messages only. Ignore any messages from the bot.

            For each user message, assign a score between 1 and 10 for the following emotions:
            - **Happiness**
            - **Sadness**
            - **Anger**
            - **Trust**

            If the user messages do not express notable emotion (e.g., if they are greetings, pleasantries, or neutral statements), assign a neutral score of **1** to each category and indicate the "dominant_emotion" as **neutral**.

            Additionally, after assigning the emotion scores, identify the **dominant emotion** based on the scores provided. 
            - If there is a tie between emotions, choose the one that appears first in the following order: **Happiness > Sadness > Anger > Trust**.
            - If the scores are all equal (i.e., all 1), the dominant emotion should also be marked as **neutral**.

            Here's the conversation with only the user messages:
            "{chunk}"

            Please respond with **only the following JSON format** (no other text or explanation):

            {{
                "happiness": score,         # The score for happiness (1-10)
                "sadness": score,           # The score for sadness (1-10)
                "anger": score,             # The score for anger (1-10)
                "trust": score,             # The score for trust (1-10)
                "dominant_emotion": "emotion"  # The emotion with the highest score (or "neutral" if scores are tied or neutral)
            }}
            """

            # Call the OpenAI API for sentiment analysis
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": sentiment_prompt}]
            )

            print("Raw API Response:", response)

            if not response or not response.choices:
                print("Empty or invalid response from OpenAI.")
                continue  # Skip if response is invalid or empty

            raw_response_content = response.choices[0].message.content.strip()
            print("Raw Response from OpenAI:", raw_response_content)

            # Check for "No sentiment detected" response
            if "No sentiment detected" in raw_response_content:
                continue  # Skip this chunk if no sentiment detected

            # Convert the response string into a dictionary using json.loads
            try:
                sentiment_scores = json.loads(raw_response_content)
            except json.JSONDecodeError as e:
                print(f"Error parsing response: {str(e)}")
                continue

            sentiment_results.append(sentiment_scores)

        # Combine results from all chunks (for example, you could average the scores)
        if not sentiment_results:
            return None

        final_sentiment = {}
        for result in sentiment_results:
            for emotion in ['happiness', 'sadness', 'anger', 'trust']:
                if emotion in final_sentiment:
                    final_sentiment[emotion] += result.get(emotion, 0)
                else:
                    final_sentiment[emotion] = result.get(emotion, 0)

        # Average the scores
        num_chunks = len(sentiment_results)
        for emotion in final_sentiment:
            final_sentiment[emotion] /= num_chunks

         # Check if all scores are neutral (1 for each emotion)
        if all(final_sentiment[emotion] == 1 for emotion in ['happiness', 'sadness', 'anger', 'trust']):
            final_sentiment['dominant_emotion'] = "neutral"
        else:
            # Find dominant emotion based on highest score
            final_sentiment['dominant_emotion'] = max(final_sentiment, key=final_sentiment.get)


        return final_sentiment

    except Exception as e:
        print(f"Error in analyze_sentiment: {str(e)}")
        return None

# Define the get_gradient function
def get_gradient(score):
    """Map a score to a gradient of emotion intensity."""
    if score <= 3:
        return "Low"
    elif 4 <= score <= 6:
        return "Moderate"
    elif score >= 7:
        return "High"
    return "Unknown"

@api_view(['POST'])  # Ensures the view only accepts POST requests
def analyze_sentiment_for_conversation(request, conversation_id):
    """Perform sentiment analysis for a specific conversation and store the result."""
    try:
        # Fetch the conversation using the provided ID
        conversation = get_object_or_404(Conversation, conversation_id=conversation_id)

        # Get the text from the conversation (assuming 'message' field contains the conversation text)
        text = conversation.messages
        if not text:  # Handle the case where the text is empty
            return JsonResponse({'error': 'No conversation messages found.'}, status=400)

        # Perform sentiment analysis
        sentiment_scores = analyze_sentiment(text)

        print("Sentiment Scores Response:", sentiment_scores)

        if not sentiment_scores or "error" in sentiment_scores:
            return JsonResponse({'error': 'No sentiment detected or failed to analyze.'}, status=400)

         # Extract sentiment scores
        joy_score = sentiment_scores.get("happiness", 0)
        sadness_score = sentiment_scores.get("sadness", 0)
        anger_score = sentiment_scores.get("anger", 0)
        trust_score = sentiment_scores.get("trust", 0)

        # Find the dominant emotion or set to "neutral" if all emotions are equal
        emotions = {
            "happiness": joy_score,
            "sadness": sadness_score,
            "anger": anger_score,
            "trust": trust_score
        }
        
        if len(set(emotions.values())) == 1:  # All values are the same
            dominant_emotion = "neutral"
        else:
            dominant_emotion = max(emotions, key=emotions.get)  # Return the highest score emotion

        # Map scores to intensity levels
        joy_gradient = get_gradient(joy_score)
        sadness_gradient = get_gradient(sadness_score)
        anger_gradient = get_gradient(anger_score)
        trust_gradient = get_gradient(trust_score)

         # Check if there's already a SentimentAnalysis entry for the conversation_id
        existing_sentiment = SentimentAnalysis.objects.filter(conversation_id=conversation.id).first()

        if existing_sentiment:
            # Update the existing entry
            existing_sentiment.joy_score = joy_score
            existing_sentiment.sadness_score = sadness_score
            existing_sentiment.anger_score = anger_score
            existing_sentiment.trust_score = trust_score
            existing_sentiment.dominant_emotion = dominant_emotion
            existing_sentiment.contact_id = conversation.contact_id
            existing_sentiment.save()  # Save the updated entry

        else:
            # Create a new entry if no existing sentiment found
            SentimentAnalysis.objects.create(
                user=conversation.user,  # Assuming the Conversation model has a 'user' field
                conversation_id=conversation.id,
                joy_score=joy_score,
                sadness_score=sadness_score,
                anger_score=anger_score,
                trust_score=trust_score,
                dominant_emotion=dominant_emotion,
                contact_id=conversation.contact_id  # Assuming 'contact_id' field in Conversation model
            )

        # Return the response including the sentiment scores and their gradients
        return JsonResponse({
            'message': 'Sentiment analysis completed successfully',
            'sentiment': {
                'happiness': {
                    'score': joy_score,
                    'intensity': joy_gradient
                },
                'sadness': {
                    'score': sadness_score,
                    'intensity': sadness_gradient
                },
                'anger': {
                    'score': anger_score,
                    'intensity': anger_gradient
                },
                'trust': {
                    'score': trust_score,
                    'intensity': trust_gradient
                },
                'dominant_emotion': dominant_emotion
            }
        })

    except Exception as e:
        print(f"Error analyzing sentiment for conversation: {str(e)}")
        return JsonResponse({'error': 'An error occurred during sentiment analysis.'}, status=500)