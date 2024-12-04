from simplecrm.models import CustomUser
import requests
from datetime import timedelta
from interaction.models import Conversation as InteractionConversation  # Import the interaction Conversation model
from communication.models import Conversation as CommunicationConversation  # Import the communication Conversation model
from contacts.models import Contact
from django.utils import timezone

def group_conversations_into_conversations(tenant_id):
    try:
        # Fetch only conversations from the interaction model that haven't been mapped, ordered by date_time
        conversations = InteractionConversation.objects.filter(mapped=False).order_by('date_time')
        print(f"Total unmapped conversations fetched: {conversations.count()}")  # Log the number of fetched conversations

        if conversations.count() == 0:
            print("No unmapped conversations found.")

        # Group conversations by contact_id and platform
        grouped_conversations = {}
        for conversation in conversations:
            key = (conversation.contact_id, conversation.source)  # Group by contact_id and source (platform)
            if key not in grouped_conversations:
                grouped_conversations[key] = []
            grouped_conversations[key].append(conversation)

        print(f"Total groups created: {len(grouped_conversations)}")  # Log the number of groups

        # Now process the grouped conversations to create new communication conversations
        for (contact_id, platform), conversation_group in grouped_conversations.items():
            print(f"Processing group for ContactID={contact_id}, Platform={platform}, Conversation count: {len(conversation_group)}")
            current_conversation_group = []

            # Sort the conversations by date_time
            conversation_group.sort(key=lambda x: x.date_time)

            for conversation in conversation_group:
                if not current_conversation_group:
                    current_conversation_group.append(conversation)
                else:
                    last_conversation_time = current_conversation_group[-1].date_time
                    # Set a time threshold (e.g., 30 minutes)
                    if conversation.date_time - last_conversation_time <= timedelta(minutes=30):
                        current_conversation_group.append(conversation)
                    else:
                        # Save the current conversation group to the database
                        save_conversation_from_group(current_conversation_group, contact_id, platform, tenant_id)
                        current_conversation_group = [conversation]

            if current_conversation_group:
                save_conversation_from_group(current_conversation_group, contact_id, platform, tenant_id)

    except Exception as e:
        # Propagate the error to be handled in the view
        raise e


def save_conversation_from_group(conversation_group, contact_id, platform, tenant_id):
    try:
        # Get the contact associated with the contact_id
        contact = Contact.objects.get(phone=contact_id, tenant_id=tenant_id)

        # Combine the conversation texts from the group into a single string
        combined_conversations = "\n".join([f"{conversation.date_time}[{conversation.sender}]: {conversation.message_text}" for conversation in conversation_group])

        # Create a unique conversation_id using the contact_id and current timestamp
        conversation_id = f"{contact_id}_{platform}_{timezone.now().timestamp()}"
         # Fetch the user based on the sender field of the first conversation in the group
        try:
            user = CustomUser.objects.get(username=conversation_group[0].user)
        except CustomUser.DoesNotExist:
            user = None  # If the user doesn't exist, set it to None

        # Create a new conversation in the Communication app's Conversation model
        new_conversation = CommunicationConversation.objects.create(
            user=user,  # Set the sender
            conversation_id=conversation_id,  # Unique conversation ID
            messages=combined_conversations,  # Combined conversations as a single string
            platform=platform,  # Platform (e.g., WhatsApp)
            contact_id=contact  # ForeignKey to the contact
        )

        print(f"Conversation saved in Communication app: ID={new_conversation.id}, Contact_ID={contact_id}, Platform={platform}")

        # Mark all conversations in the group as mapped
        for conversation in conversation_group:
            conversation.mapped = True
            conversation.save()
            print(f"Marked conversation as mapped: {conversation.id}")


    except Contact.DoesNotExist:
        error_message = f"Contact not found for ContactID={contact_id}, TenantID={tenant_id}"
        print(error_message)
        # Raise a ValueError to propagate the error
        raise ValueError(error_message)
    
    except Exception as e:
        print(f"Error while saving conversation: {str(e)}")
        # Raise the general exception to be caught in the view
        raise e
