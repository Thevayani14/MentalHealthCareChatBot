import streamlit as st
from pymongo import MongoClient
from bson.objectid import ObjectId # To handle MongoDB's _id
import datetime

# --- DATABASE CONNECTION ---
def get_db_connection():
    """Establishes a connection to the MongoDB database."""
    try:
        # Get the connection string from Streamlit secrets
        uri = st.secrets["MONGO_URI"]
        client = MongoClient(uri)
        # You can add a ping to check the connection
        client.admin.command('ping')
        # st.toast("Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {e}")
        return None

def get_db():
    """Returns a specific database (e.g., 'mental_health_app') from the client."""
    client = get_db_connection()
    if client:
        return client.mental_health_app # Name your database here
    return None

# --- USER FUNCTIONS ---
def add_user(username, hashed_password):
    db = get_db()
    if db is None: return False
    users_collection = db.users
    # Check if user already exists to provide a better error
    if users_collection.find_one({"username": username}):
        return False # Indicates user exists
    
    users_collection.insert_one({
        "username": username,
        "hashed_password": hashed_password
    })
    return True

def get_user(username):
    db = get_db()
    if db is None: return None
    users_collection = db.users
    user_data = users_collection.find_one({"username": username})
    if user_data:
        # Convert ObjectId to string for session state compatibility
        user_data['_id'] = str(user_data['_id'])
    return user_data

# --- CONVERSATION & MESSAGE FUNCTIONS ---
def create_conversation(user_id):
    """Creates a new conversation document."""
    db = get_db()
    if db is None: return None
    conversations_collection = db.conversations
    result = conversations_collection.insert_one({
        "user_id": ObjectId(user_id), # Store as ObjectId
        "title": "New Chat",
        "start_time": datetime.datetime.now(datetime.timezone.utc),
        "messages": []
    })
    return str(result.inserted_id)

def get_user_conversations(user_id):
    """Retrieves all conversation titles for a user."""
    db = get_db()
    if db is None: return []
    conversations_collection = db.conversations
    # Find conversations and project only the needed fields (_id, title)
    convs = conversations_collection.find(
        {"user_id": ObjectId(user_id)},
        {"title": 1, "start_time": 1}
    ).sort("start_time", -1) # -1 for descending order (most recent first)
    
    # Convert to a list of dicts with string IDs
    return [{"id": str(c["_id"]), "title": c["title"]} for c in convs]


def update_conversation_title(conversation_id, new_title):
    db = get_db()
    if db is None: return
    conversations_collection = db.conversations
    conversations_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"title": new_title}}
    )

def add_message(conversation_id, role, content):
    """Adds a message to a conversation's 'messages' array."""
    db = get_db()
    if db is None: return
    conversations_collection = db.conversations
    message_doc = {"role": role, "content": content}
    conversations_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$push": {"messages": message_doc}}
    )

def get_messages(conversation_id):
    """Retrieves the 'messages' array from a conversation document."""
    db = get_db()
    if db is None: return []
    conversations_collection = db.conversations
    conversation = conversations_collection.find_one({"_id": ObjectId(conversation_id)})
    return conversation.get("messages", []) if conversation else []