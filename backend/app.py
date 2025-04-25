from flask import Flask, request, jsonify, send_file
from flask_pymongo import PyMongo
from flask_cors import CORS
import gridfs
import os
import pymongo
import traceback
import uuid
import json
from bson.objectid import ObjectId
import hashlib
import google.generativeai as genai
from PIL import Image
from datetime import datetime, timezone

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# API configuration for image recognition service
API_CONFIG = {
    # Using Gemini API for image recognition
    "service": "gemini",
    "api_key": "your-api-key",  # Using the same key as Gemini chat
    "enable_mock": False  # Disable mock data and use real API
}

# Large language model configuration for conversation
LLM_CONFIG = {
    # Enable/disable LLM for conversation
    "enabled": True,
    
    # Google AI Studio (Gemini) integration
    "service": "gemini",
    "api_key": "your-api-key",
    "model": "gemini-1.5-flash"
}

# Global variable to track database status
db_connection_status = {"status": "Unknown", "error": None}

# Simple MongoDB Atlas connection
try:
    print("Connecting to MongoDB Atlas...")
    # Standard MongoDB connection string
    mongodb_uri = "your-mongodb-connection-string"
    
    # Configure Flask app to use MongoDB
    app.config["MONGO_URI"] = mongodb_uri
    mongo = PyMongo(app)
    
    # Test connection with a simple command
    mongo.db.command('ping')
    print("Connected to MongoDB Atlas successfully")
    db_connection_status["status"] = "Connected"
    
except Exception as e:
    print(f"MongoDB connection error: {str(e)}")
    db_connection_status["status"] = "Error"
    db_connection_status["error"] = str(e)
    raise

# Ensuring uploads directory exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize Gemini API
# Ensuring API key is valid and configured
gemini_api_key = API_CONFIG.get("api_key")
if gemini_api_key:
    try:
        print(f"Attempting to configure Gemini API with key ending in: ...{gemini_api_key[-4:]}")
        genai.configure(api_key=gemini_api_key)
        print("Gemini API configured successfully using API Key.")
    except Exception as api_conf_error:
        print(f"ERROR configuring Gemini API: {api_conf_error}")

else:
    print("WARNING: Gemini API key not found in API_CONFIG. Gemini features may fail.")

# Helper function for text generation using the configured LLM
def generate_text_with_llm(prompt):
    """Generates text using the configured conversational LLM."""
    if not LLM_CONFIG.get("enabled", False):
        print("LLM is disabled. Cannot generate text.")
        return "Error: LLM is disabled."
    
    try:
        model_name = LLM_CONFIG.get("model", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        print(f"Generating text with {model_name}...")
        response = model.generate_content(prompt)
        
        if response and hasattr(response, 'text'):
            return response.text.strip()
        elif response and hasattr(response, 'parts') and response.parts:
             return response.parts[0].text.strip()
        else:
            # Handle potential errors or empty responses
            print(f"LLM text generation returned unexpected response: {response}")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                 return f"Error: Text generation blocked ({response.prompt_feedback.block_reason})"
            return "Error: Failed to generate text."
            
    except Exception as e:
        print(f"Error during LLM text generation: {str(e)}")
        traceback.print_exc()
        return f"Error: {str(e)}"

def call_vision_api(image_path, service=None):
    """
    Call the appropriate vision API based on configuration.
    Returns a textual description of the image using gemini-pro-vision.
    """
    if not service:
        service = API_CONFIG.get("service", "gemini")


    if image_path is None or not os.path.exists(image_path):
        print("No valid image path provided")
        return "Error: Invalid image path provided."

    # Gemini API for image recognition (gemini-pro-vision)
    if service == "gemini":
        try:
            print(f"\n=== Calling Gemini Vision API (gemini-pro-vision) ===")
            print(f"Image path: {image_path}")

            # Load the image using PIL
            img = Image.open(image_path)
            print(f"Image loaded successfully: {img.size} pixels, Format: {img.format}")

            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = "Describe this image in detail. What objects, scenes, or people are visible?"

            print("Sending request to Gemini Vision API...")

            # Generate content using the image and prompt
            response = model.generate_content([prompt, img]) # Pass prompt first generally works well

            # Process the response
            if response and hasattr(response, 'text'):
                text_response = response.text
                print(f"Gemini Vision API response received: {text_response[:200]}...")
                return text_response
            else:
                # Handling cases where the response might be blocked or empty
                print("Gemini Vision API returned an empty or unexpected response.")
                if hasattr(response, 'prompt_feedback'):
                    print(f"Prompt Feedback: {response.prompt_feedback}")
                return "Error: Failed to get description from Vision API (empty response)."

        except FileNotFoundError:
            print(f"Error: Image file not found at {image_path}")
            return "Error: Image file not found."
        except Exception as e:
            raw_error_message = str(e)
            print(f"Error using Gemini Vision API: {raw_error_message}")
            traceback.print_exc()
            return f"Error: {raw_error_message}"

    # If no service matched or service is not implemented, return error string
    print(f"Unknown or unimplemented vision service: {service}")
    return f"Error: Unknown vision service '{service}' specified."

# Image analysis function - now returns description
def analyze_image(image_path=None, image_id=None):
    """
    Analyze image content using the configured vision API.
    Retrieves image from GridFS if image_id is provided.
    Returns a dictionary containing success status and description/error.
    """
    temp_file_to_delete = None
    try:
        print(f"\n=== Starting Image Analysis ===")
        print(f"Provided image path: {image_path}")
        print(f"Provided image ID: {image_id}")

        analysis_image_path = image_path

        # If we have an image_id, retrieve the file from GridFS
        if image_id and not image_path:
            fs = gridfs.GridFS(mongo.db)
            try:
                if not ObjectId.is_valid(image_id):
                     print(f"Invalid ObjectId format for image_id: {image_id}")
                     return {"success": False, "error": "Invalid image ID format."}

                file_data = fs.get(ObjectId(image_id))
                print(f"Retrieved file from GridFS: {file_data.filename}")

                # Create a temporary file to process
                temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{uuid.uuid4()}_{file_data.filename}")
                with open(temp_path, 'wb') as f:
                    f.write(file_data.read())
                analysis_image_path = temp_path
                temp_file_to_delete = temp_path
                print(f"Created temporary file for analysis at: {analysis_image_path}")

            except gridfs.errors.NoFile:
                 print(f"Error: No file found in GridFS for image_id: {image_id}")
                 return {"success": False, "error": "Image file not found in storage."}
            except Exception as grid_error:
                print(f"Error retrieving file from GridFS: {str(grid_error)}")
                traceback.print_exc()
                return {"success": False, "error": f"File retrieval error: {str(grid_error)}"}

        if not analysis_image_path or not os.path.exists(analysis_image_path):
            error_msg = f"Image path for analysis is invalid or file does not exist: {analysis_image_path}"
            print(error_msg)
            return {"success": False, "error": error_msg}


        print(f"Calling vision API for image: {analysis_image_path}")
        description_or_error = call_vision_api(analysis_image_path)
        print(f"Vision API returned: {description_or_error[:200]}...")

        if isinstance(description_or_error, str) and description_or_error.startswith("Error:"):
            return {"success": False, "error": description_or_error}
        else:
            
            return {"success": True, "description": description_or_error}

    except Exception as e:
        print(f"Error analyzing image: {str(e)}")
        traceback.print_exc()
        return {"success": False, "error": f"Unexpected error during analysis: {str(e)}"}
    finally:
        if temp_file_to_delete and os.path.exists(temp_file_to_delete):
            try:
                os.remove(temp_file_to_delete)
                print(f"Deleted temporary analysis file: {temp_file_to_delete}")
            except Exception as del_error:
                print(f"Error deleting temporary file {temp_file_to_delete}: {del_error}")

@app.route('/status', methods=['GET'])
def status():
    """Endpoint to check server and database status"""
    return jsonify({
        "server": "running",
        "database": db_connection_status
    })

@app.route('/register', methods=['POST'])
def register_user():
    """Register a new user"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({"error": "Missing required fields"}), 400
            
        existing_user = mongo.db.users.find_one({"email": email})
        if existing_user:
            return jsonify({"error": "User with this email already exists"}), 409
            
        user_id = str(uuid.uuid4())
        

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Save user to database
        mongo.db.users.insert_one({
            "_id": user_id,
            "username": username,
            "email": email,
            "password": hashed_password,
            "created_at": datetime.datetime.utcnow(),
            "last_login": None,
            "preferences": {
                "theme": "light",
                "notifications_enabled": True
            }
        })
        
        return jsonify({
            "message": "User registered successfully",
            "user_id": user_id
        }), 201
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred during registration", "details": str(e)}), 500

@app.route('/login', methods=['POST'])
def login_user():
    """Login a user"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Missing required fields"}), 400
            
        # Hash password for comparison
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        user = mongo.db.users.find_one({
            "email": email,
            "password": hashed_password
        })
        
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401
            
        # Update last login time
        mongo.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.datetime.utcnow()}}
        )
        
        # Return user info
        user_info = {
            "user_id": user["_id"],
            "username": user["username"],
            "email": user["email"],
            "preferences": user.get("preferences", {})
        }
        
        return jsonify({
            "message": "Login successful",
            "user": user_info
        }), 200
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred during login", "details": str(e)}), 500

@app.route('/user/profile', methods=['GET'])
def get_user_profile():
    """Get user profile information"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"error": "No user_id provided"}), 400
            
        user = mongo.db.users.find_one({"_id": user_id})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Return user info
        user_info = {
            "user_id": user["_id"],
            "username": user["username"],
            "email": user["email"],
            "preferences": user.get("preferences", {}),
            "created_at": user.get("created_at").isoformat() if user.get("created_at") else None,
            "last_login": user.get("last_login").isoformat() if user.get("last_login") else None
        }
        
        
        # Get user's chat count
        chat_count = mongo.db.user_chat.count_documents({"user_id": user_id})
        user_info["chat_count"] = chat_count
        
        return jsonify(user_info), 200
        
    except Exception as e:
        print(f"Error retrieving user profile: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred retrieving the user profile", "details": str(e)}), 500

@app.route('/user/preferences', methods=['PUT'])
def update_user_preferences():
    """Update user preferences"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        user_id = data.get('user_id')
        preferences = data.get('preferences')
        
        if not user_id or not preferences:
            return jsonify({"error": "Missing required fields"}), 400
            
        # Update user preferences
        result = mongo.db.users.update_one(
            {"_id": user_id},
            {"$set": {"preferences": preferences}}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify({
            "message": "User preferences updated successfully"
        }), 200
        
    except Exception as e:
        print(f"Error updating user preferences: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred updating user preferences", "details": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Get user_id from request
    user_id = request.form.get('user_id', 'anonymous')
    title = request.form.get('title', file.filename)
    description_from_user = request.form.get('description', '')

    print(f"Processing upload request: file={file.filename}, user_id={user_id}")
    temp_path = None
    try:

        temp_filename = f"{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
        file.save(temp_path)
        print(f"Saved file temporarily to: {temp_path}")

        # Analyze the image to get the description from Gemini Vision
        print(f"Analyzing image using configured API: {temp_path}")
        analyze_results = analyze_image(image_path=temp_path)
        print(f"Analysis results: {analyze_results}")

        if not analyze_results.get("success"):
            analysis_error = analyze_results.get('error', 'Unknown analysis error')
            print(f"Image analysis failed: {analysis_error}")
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({
                "error": "Image analysis failed",
                "details": analysis_error
            }), 500

        # Get the vision description from analysis
        vision_description = analyze_results.get("description", "")
        print(f"Extracted vision description: {vision_description[:100]}...")

 
        generated_title = "Untitled Image"
        if vision_description and not vision_description.startswith("Error:"):
            title_prompt = f"Generate a short, descriptive title (max 5 words) for an image described as follows:\n\nDescription: {vision_description}\n\nTitle:"
            try:
                generated_title_raw = generate_text_with_llm(title_prompt)
                if generated_title_raw and not generated_title_raw.startswith("Error:"):
                    generated_title = generated_title_raw.strip('"\' ')
                    print(f"Generated title: {generated_title}")
                else:
                    print(f"Failed to generate title: {generated_title_raw}")
            except Exception as title_gen_error:
                 print(f"Error during title generation: {title_gen_error}")
        else:
             print("Skipping title generation due to missing or error in vision description.")


        # Reset file pointer before storing in GridFS
        file.seek(0)

        # Use GridFS to store the file content
        fs = gridfs.GridFS(mongo.db)
        with open(temp_path, 'rb') as temp_file_content:
             file_id = fs.put(
                 temp_file_content,
                 filename=file.filename,
                 content_type=file.content_type
             )
        print(f"Stored file in GridFS with file_id: {file_id}")

        # Save metadata to the images collection
        image_metadata = {
            "_id": ObjectId(), 
            "file_id": file_id,
            "filename": file.filename,
            "title": title,
            "description": description_from_user,
            "vision_description": vision_description,
            "generated_title": generated_title, 
            "uploadTimestamp": datetime.now(timezone.utc),
            "size": os.path.getsize(temp_path),
            "mime_type": file.content_type,
            "labels": []
        }

        result = mongo.db.images.insert_one(image_metadata)
        image_id = str(image_metadata["_id"])
        print(f"Created image document with image_id: {image_id}")

        # Record upload in the uploadsImage collection to track user uploads
        mongo.db.uploadsImage.insert_one({
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "image_id": image_id, 
            "timestamp": datetime.now(timezone.utc)
        })
        print(f"Recorded upload in uploadsImage collection for user_id: {user_id}")

        return jsonify({
            "message": "File uploaded and analyzed successfully",
            "storage": "mongodb",
            "image_id": image_id,
            "title": title,
            "description": description_from_user,
            "vision_description": vision_description,
            "generated_title": generated_title,
            "labels": image_metadata["labels"]
        }), 201 

    except Exception as e:
        # Log the error
        print(f"Upload error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "Could not upload file",
            "details": str(e)
        }), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"Deleted temporary upload file: {temp_path}")
            except Exception as del_error:
                print(f"Error deleting temporary upload file {temp_path}: {del_error}")

@app.route('/images', methods=['GET'])
def get_images():
    """Get list of uploaded images"""
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 10))
        skip = int(request.args.get('skip', 0))
        
        query = {}
        
        if user_id:
            # Get image IDs associated with the user from uploadsImage collection
            user_images = list(mongo.db.uploadsImage.find({"user_id": user_id}))
            image_ids = [ObjectId(img["image_id"]) for img in user_images]
            if image_ids:
                query["_id"] = {"$in": image_ids}
            else:
                return jsonify({"images": [], "total_count": 0}), 200
        
        total_count = mongo.db.images.count_documents(query)
            
        images = list(mongo.db.images.find(
            query,
            {"_id": 1, "filename": 1, "title": 1, "description": 1, "uploadTimestamp": 1, "labels": 1, "generated_title": 1} 
        ).sort("uploadTimestamp", -1).skip(skip).limit(limit))
        
        # Convert ObjectId to string for JSON serialization
        for img in images:
            img["_id"] = str(img["_id"])
            img["file_id"] = str(img["file_id"]) if "file_id" in img else None
            # Convert datetime to string
            if "uploadTimestamp" in img:
                img["uploadTimestamp"] = img["uploadTimestamp"].isoformat()
            img["generated_title"] = img.get("generated_title", img.get("title", img.get("filename", "Untitled")))    

        return jsonify({
            "images": images, 
            "total_count": total_count,
            "page": skip // limit + 1 if limit > 0 else 1,
            "pages": (total_count + limit - 1) // limit if limit > 0 else 1
        }), 200
        
    except Exception as e:
        print(f"Error retrieving images: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred retrieving images", "details": str(e)}), 500

@app.route('/images/<image_id>', methods=['GET'])
def get_image(image_id):
    try:
        if not ObjectId.is_valid(image_id):
            return jsonify({'error': 'Invalid image ID format'}), 400

        user_id = request.args.get('user_id')
        
        image = mongo.db.images.find_one({"_id": ObjectId(image_id)})
        
        if image is None:
            return jsonify({'error': 'Image not found'}), 404

        for key, value in image.items():
            if isinstance(value, ObjectId):
                image[key] = str(value)
            elif isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, ObjectId):
                        image[key][nested_key] = str(nested_value)
            
        if 'filename' in image:
            image['url'] = f"/uploads/{image['filename']}"
            
        image["generated_title"] = image.get("generated_title", image.get("title", image.get("filename", "Untitled")))    

        if user_id:
            try:
                mongo.db.imageViews.insert_one({
                    'user_id': user_id,
                    'image_id': image_id,
                    'timestamp': datetime.datetime.now(timezone.utc),
                    'referrer': request.referrer or 'direct',
                    'user_agent': request.user_agent.string
                })
            except Exception as e:
                print(f"Error recording image view: {str(e)}")

        return jsonify(image), 200
        
    except Exception as e:
        print(f"Error getting image: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to get image'}), 500

@app.route('/image/<image_id>', methods=['PUT'])
def update_image(image_id):
    """Update image metadata"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        title = data.get('title')
        description = data.get('description')
        
        update_fields = {}
        if title is not None:
            update_fields["title"] = title
        if description is not None:
            update_fields["description"] = description
            
        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400
            
        result = mongo.db.images.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Image not found"}), 404
            
        return jsonify({
            "message": "Image updated successfully",
            "updated_fields": list(update_fields.keys())
        }), 200
        
    except Exception as e:
        print(f"Error updating image: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred updating the image", "details": str(e)}), 500

@app.route('/image/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete an image and all related data"""
    try:
        image = mongo.db.images.find_one({"_id": ObjectId(image_id)})
        
        if not image:
            return jsonify({"error": "Image not found"}), 404
            
        file_id = image.get("file_id")
        
        if file_id:
            fs = gridfs.GridFS(mongo.db)
            if fs.exists(ObjectId(file_id)):
                fs.delete(ObjectId(file_id))
        
        # Delete all related data from different collections
        # 1. Delete from images collection
        mongo.db.images.delete_one({"_id": ObjectId(image_id)})
        
        # 2. Delete from uploadsImage collection
        mongo.db.uploadsImage.delete_many({"image_id": image_id})
        
        # 3. Delete from imageViews collection
        mongo.db.imageViews.delete_many({"image_id": image_id})
        
        # 4. Find chat history related to this image
        chat_records = list(mongo.db.chatHistory.find({"image_id": image_id}))
        chat_ids = [chat["_id"] for chat in chat_records]
        
        # 5. Delete from chatHistory collection
        mongo.db.chatHistory.delete_many({"image_id": image_id})
        
        # 6. Delete from user_chat collection for the found chat_ids
        if chat_ids:
            mongo.db.user_chat.delete_many({"chat_history_id": {"$in": chat_ids}})
        
        return jsonify({
            "message": "Image and all related data deleted successfully"
        }), 200
        
    except Exception as e:
        print(f"Error deleting image: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred deleting the image", "details": str(e)}), 500
        
@app.route('/analytics/images', methods=['GET'])
def get_image_analytics():
    """Get analytics data about image views"""
    try:
        user_id = request.args.get('user_id')
        
        pipeline = [
            {"$group": {
                "_id": "$image_id",
                "view_count": {"$sum": 1},
                "last_viewed": {"$max": "$timestamp"}
            }},
            {"$sort": {"view_count": -1}}
        ]
        
        if user_id:
            user_images = list(mongo.db.uploadsImage.find({"user_id": user_id}))
            image_ids = [img["image_id"] for img in user_images]
            
            if image_ids:
                pipeline.insert(0, {"$match": {"image_id": {"$in": image_ids}}})
        
        view_stats = list(mongo.db.imageViews.aggregate(pipeline))
        
        for stat in view_stats:
            try:
                image = mongo.db.images.find_one({"_id": ObjectId(stat["_id"])})
                if image:
                    stat["title"] = image.get("title", image.get("filename", "Unknown"))
                    stat["filename"] = image.get("filename", "Unknown")
                else:
                    stat["title"] = "Image not found"
                    stat["filename"] = "Unknown"
            except:
                stat["title"] = "Error retrieving image"
                stat["filename"] = "Unknown"
                
            if "last_viewed" in stat:
                stat["last_viewed"] = stat["last_viewed"].isoformat()
        
        return jsonify({
            "image_view_stats": view_stats
        }), 200
        
    except Exception as e:
        print(f"Error retrieving image analytics: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred retrieving image analytics", "details": str(e)}), 500

@app.route('/analytics/user-activity', methods=['GET'])
def get_user_activity():
    """Get analytics data about user activity"""
    try:
        view_pipeline = [
            {"$group": {
                "_id": "$user_id",
                "view_count": {"$sum": 1},
                "last_active": {"$max": "$timestamp"}
            }},
            {"$sort": {"view_count": -1}},
            {"$limit": 10}
        ]
        
        view_stats = list(mongo.db.imageViews.aggregate(view_pipeline))
        
        upload_pipeline = [
            {"$group": {
                "_id": "$user_id",
                "upload_count": {"$sum": 1},
                "last_upload": {"$max": "$timestamp"}
            }},
            {"$sort": {"upload_count": -1}},
            {"$limit": 10}
        ]
        
        upload_stats = list(mongo.db.uploadsImage.aggregate(upload_pipeline))
        
        chat_pipeline = [
            {"$group": {
                "_id": "$user_id",
                "chat_count": {"$sum": 1}
            }},
            {"$sort": {"chat_count": -1}},
            {"$limit": 10}
        ]
        
        chat_stats = list(mongo.db.user_chat.aggregate(chat_pipeline))
        
        for stats_list in [view_stats, upload_stats, chat_stats]:
            for stat in stats_list:
                if stat["_id"] == "anonymous":
                    stat["username"] = "Anonymous"
                    continue
                    
                try:
                    user = mongo.db.users.find_one({"_id": stat["_id"]})
                    if user:
                        stat["username"] = user.get("username", "Unknown")
                        stat["email"] = user.get("email", "Unknown")
                    else:
                        stat["username"] = "User not found"
                except:
                    stat["username"] = "Error retrieving user"
                
                for date_field in ["last_active", "last_upload"]:
                    if date_field in stat:
                        stat[date_field] = stat[date_field].isoformat()
        
        return jsonify({
            "most_active_viewers": view_stats,
            "most_active_uploaders": upload_stats,
            "most_active_chatters": chat_stats
        }), 200
        
    except Exception as e:
        print(f"Error retrieving user activity analytics: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred retrieving user activity analytics", "details": str(e)}), 500

def conversation_with_llm(query, image_info, context=None):
    """
    Generate a conversational response about an image using Google's Gemini model.
    
    Args:
        query: User's question
        image_info: Image metadata (used for title primarily now)
        context: The AI-generated description of the image from gemini-pro-vision
        
    Returns:
        Generated response text
    """
    if not LLM_CONFIG.get("enabled", False):
        print("LLM is disabled, returning basic response.")
        return f"LLM is disabled. The image is titled '{image_info.get('title', 'Unknown')}'."
    
    try:
        print("LLM is enabled, attempting to use Gemini...")
        image_description = context if context else image_info.get('vision_description')
        
        if not image_description or image_description.startswith("Error:"):
            print(f"Image analysis failed or description is missing. Error/Description: {image_description}")
            return f"Sorry, I couldn't analyze the image ('{image_info.get('title', 'Unknown')}'). The analysis step reported: {image_description if image_description else 'No description generated.'}"
        
        print(f"Using image description for LLM context: {image_description[:150]}...")
        
        system_prompt = (
            f"You are an assistant that helps users understand images based on a provided description. "
            f"The image title is: '{image_info.get("title", "Unknown")}'.\n"
            f"The description of the image is:\n---\n{image_description}\n---"
            f"\nBased *only* on this description, please answer the user's questions about the image. "
            f"Be conversational and helpful. If the description doesn't contain the answer, "
            f"state that the information isn't available in the description.\n\n"
            f"IMPORTANT INSTRUCTIONS:\n"
            f"1. Keep your answers SHORT and PRECISE - ideally 1-3 sentences maximum.\n"
            f"2. Base your answers strictly on the provided image description.\n"
            f"3. Do not invent details not present in the description.\n"
            f"4. Do not apologize for limitations or use phrases like 'Based on the description...' unless necessary to explain a limitation.\n"
            f"5. Focus on answering the specific question asked."
        )
        
        # Google AI Studio (Gemini) integration
        try:
            model_name = LLM_CONFIG.get("model", "gemini-1.5-flash") 
            print(f"Using Gemini conversational model: {model_name}")
            model = genai.GenerativeModel(model_name)
            
            full_prompt = f"{system_prompt}\n\nUser's question: {query}"
            print(f"Sending prompt to Gemini (length: {len(full_prompt)}):")
            
            try:
                print("Generating content with Gemini API...")
                response = model.generate_content(full_prompt)
                
                # Process the response
                response_text = None
                if response and hasattr(response, 'text'):
                    response_text = response.text
                    print(f"Got response from Gemini: {response_text[:100]}...")
                elif response and hasattr(response, 'parts') and response.parts:
                     response_text = response.parts[0].text
                     print(f"Got response from Gemini (parts): {response_text[:100]}...")
                elif response and hasattr(response, 'candidates') and response.candidates:
                     try:
                         response_text = response.candidates[0].content.parts[0].text
                         print(f"Got response from Gemini (candidates): {response_text[:100]}...")
                     except (AttributeError, IndexError):
                         print(f"Could not extract text from Gemini candidates structure: {response.candidates}")
                         response_text = "Error: Could not process LLM response structure."
                else:
                    print(f"Unexpected response format from Gemini: {type(response)}")
                    print(f"Response content: {response}")
                    if hasattr(response, 'prompt_feedback'):
                        print(f"Prompt Feedback: {response.prompt_feedback}")
                        if response.prompt_feedback.block_reason:
                            response_text = f"Response blocked due to: {response.prompt_feedback.block_reason}"
                    if not response_text:
                         response_text = "Error: Received unexpected response format from LLM."
                
                return response_text.strip()
                
            except Exception as gen_error:
                print(f"Error generating content with Gemini: {str(gen_error)}")
                traceback.print_exc()
                return "Sorry, I encountered an error trying to generate a response."
            
        except ImportError as e:
            print(f"Error importing Gemini library: {str(e)}")
            traceback.print_exc()
            return "Error: LLM library not available."
        except Exception as gemini_error:
            print(f"Gemini API configuration or call error: {str(gemini_error)}")
            traceback.print_exc()
            return "Error: Could not connect to the conversational AI service."
            
    except Exception as e:
        print(f"Error in conversation_with_llm function: {str(e)}")
        traceback.print_exc()
        return "An unexpected error occurred while processing the chat request."

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        user_message = data.get('message')
        image_id = data.get('image_id')
        user_id = data.get('user_id', 'anonymous')
        
        if not user_message or not image_id:
            return jsonify({"error": "Message and image_id are required"}), 400
            
        if not ObjectId.is_valid(image_id):
            return jsonify({"error": "Invalid image_id format"}), 400

        image_info = mongo.db.images.find_one({"_id": ObjectId(image_id)})
        if not image_info:
            return jsonify({"error": "Image not found"}), 404
        
        context_description = image_info.get('vision_description')
        if not context_description:
             labels = image_info.get('labels', [])
             if labels:
                 context_description = "Detected labels: " + ", ".join([l.get('label', str(l)) for l in labels])
             else:
                 context_description = "No description or labels available for this image."

        response_text = conversation_with_llm(user_message, image_info, context=context_description) # Pass description as context

        # --- Save Chat History ---
        chat_history_id = ObjectId() # Unique ID for this conversation turn

        # Save user message
        user_chat_entry = {
            "_id": ObjectId(), # Unique ID for this specific message
            "conversation_id": chat_history_id,
            "user_id": user_id,
            "image_id": image_id,
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now(timezone.utc)
        }
        mongo.db.chatHistory.insert_one(user_chat_entry)

        # Save bot response
        bot_chat_entry = {
            "_id": ObjectId(), 
            "conversation_id": chat_history_id,
            "user_id": user_id,
            "image_id": image_id,
            "role": "bot",
            "content": response_text,
            "timestamp": datetime.now(timezone.utc)
        }
        mongo.db.chatHistory.insert_one(bot_chat_entry)


        return jsonify({
            "response": response_text,
            "image_id": image_id,
            "conversation_id": str(chat_history_id)
        }), 200
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Failed to process chat request", "details": str(e)}), 500

@app.route('/chat-history', methods=['GET'])
def get_chat_history():
    try:
        user_id = request.args.get('user_id')
        image_id = request.args.get('image_id')

        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        query = {"user_id": user_id}
        if image_id:
            query["image_id"] = image_id
            
        chat_history = list(mongo.db.chatHistory.find(
            query,
            {
                "_id": 1,
                "role": 1,
                "content": 1,
                "timestamp": 1,
                "image_id": 1
            }
        ).sort("timestamp", 1))
        
        image_ids = list(set(chat["image_id"] for chat in chat_history if "image_id" in chat))
        
        images = {}
        for img_id_str in image_ids:
            try:
                img_object_id = ObjectId(img_id_str)
                image = mongo.db.images.find_one(
                    {"_id": img_object_id},
                    {"title": 1, "filename": 1, "generated_title": 1} 
                )
                if image:
                    chat_title = image.get("generated_title", image.get("title", image.get("filename", "Chat about Image")))
                    images[img_id_str] = {
                        "chat_summary_title": chat_title,
                        "url": f"/uploads/{image.get('filename', '')}" if image.get('filename') else None
                    }
                else:
                     images[img_id_str] = {"chat_summary_title": "Image Deleted", "url": None}
            except Exception as img_fetch_error:
                 print(f"Error fetching image details for {img_id_str}: {img_fetch_error}")
                 images[img_id_str] = {"chat_summary_title": "Error Fetching Title", "url": None}
        
        formatted_history = []
        for chat in chat_history:
            img_id = str(chat.get("image_id")) if chat.get("image_id") else None
            
            role = chat.get("role")
            if not role:
                if "response" in chat:
                    role = "bot"
                else:
                    role = "user"
            
            content = chat.get("content")
            if not content and "response" in chat:
                content = chat["response"]
            
            formatted_chat = {
                "id": str(chat["_id"]),
                "role": role,
                "content": content or "",
                "timestamp": chat["timestamp"].isoformat() if chat.get("timestamp") else None,
                "image_id": img_id,
                "chat_summary_title": images.get(img_id, {}).get("chat_summary_title") if img_id else "General Chat", 
                "image_url": images.get(img_id, {}).get("url") if img_id else None
            }
            formatted_history.append(formatted_chat)
            
        return jsonify({"chat_history": formatted_history}), 200
        
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Failed to get chat history"}), 500

@app.route('/chat-history/<image_id>', methods=['DELETE'])
def delete_chat_history(image_id):
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        # Deleting all chat history for this image and user
        result = mongo.db.chatHistory.delete_many({
            "user_id": user_id,
            "image_id": image_id
        })
        
        # Also deleting the user-chat mapping
        mongo.db.user_chat.delete_many({
            "user_id": user_id,
            "chat_history_id": {"$in": [str(chat["_id"]) for chat in mongo.db.chatHistory.find({"image_id": image_id})]}
        })
        
        return jsonify({
            "message": "Chat history deleted successfully",
            "deleted_count": result.deleted_count
        }), 200
        
    except Exception as e:
        print(f"Error deleting chat history: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Failed to delete chat history"}), 500

@app.route('/recommendations', methods=['GET'])
def get_recommendations():
    """Get personalized image recommendations for a user based on their activity"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"error": "No user_id provided"}), 400
            
        user = mongo.db.users.find_one({"_id": user_id}) if user_id != 'anonymous' else None
        
        view_history = list(mongo.db.imageViews.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(20))
        
        chat_history = list(mongo.db.chatHistory.find(
            {"user_id": user_id},
            {"query": 1}
        ).sort("timestamp", -1).limit(20))
        
        viewed_image_ids = [view["image_id"] for view in view_history]
        
        topics_of_interest = []
        for chat in chat_history:
            query = chat.get("query", "").lower()
            words = query.split()
            for word in words:
                if len(word) > 3 and word not in ["what", "where", "when", "this", "that", "there", "image", "picture"]:
                    topics_of_interest.append(word)
        
        topic_frequency = {}
        for topic in topics_of_interest:
            if topic in topic_frequency:
                topic_frequency[topic] += 1
            else:
                topic_frequency[topic] = 1
        
        top_topics = sorted(topic_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
        top_topic_words = [topic[0] for topic in top_topics]
        
        recommendations = []
        
        # 1. Similar images based on labels
        if viewed_image_ids:
            viewed_images = list(mongo.db.images.find({"_id": {"$in": [ObjectId(id) for id in viewed_image_ids]}}))
            
            all_labels = []
            for img in viewed_images:
                labels = img.get("labels", [])
                if labels:
                    all_labels.extend([l["label"] for l in labels if isinstance(l, dict) and "label" in l])
            
            label_frequency = {}
            for label in all_labels:
                if label in label_frequency:
                    label_frequency[label] += 1
                else:
                    label_frequency[label] = 1
            
            common_labels = sorted(label_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
            common_label_words = [label[0] for label in common_labels]
            
            label_pipeline = [
                {"$match": {"labels.label": {"$in": common_label_words}}},
                {"$match": {"_id": {"$nin": [ObjectId(id) for id in viewed_image_ids]}}},
                {"$limit": 5}
            ]
            
            similar_images = list(mongo.db.images.aggregate(label_pipeline))
            
            for img in similar_images:
                img["_id"] = str(img["_id"])
                img["file_id"] = str(img["file_id"]) if "file_id" in img else None
                if "uploadTimestamp" in img:
                    img["uploadTimestamp"] = img["uploadTimestamp"].isoformat()
                img["recommendation_reason"] = "Based on images you've viewed"
                recommendations.append(img)
        
        # 2. Popular images (most viewed)
        popular_pipeline = [
            {"$group": {
                "_id": "$image_id",
                "view_count": {"$sum": 1}
            }},
            {"$sort": {"view_count": -1}},
            {"$limit": 5}
        ]
        
        popular_image_ids = list(mongo.db.imageViews.aggregate(popular_pipeline))
        
        for item in popular_image_ids:
            image_id = item["_id"]
            if image_id in viewed_image_ids or any(rec["_id"] == image_id for rec in recommendations):
                continue
                
            try:
                image = mongo.db.images.find_one({"_id": ObjectId(image_id)})
                if image:
                    image["_id"] = str(image["_id"])
                    image["file_id"] = str(image["file_id"]) if "file_id" in image else None
                    if "uploadTimestamp" in image:
                        image["uploadTimestamp"] = image["uploadTimestamp"].isoformat()
                    image["recommendation_reason"] = f"Popular image with {item['view_count']} views"
                    recommendations.append(image)
            except Exception as e:
                print(f"Error getting popular image {image_id}: {str(e)}")
        
        # 3. Recent uploads
        recent_uploads = list(mongo.db.images.find(
            {"_id": {"$nin": [ObjectId(id) for id in viewed_image_ids]}},
            {"_id": 1, "filename": 1, "title": 1, "description": 1, "uploadTimestamp": 1, "labels": 1, "file_id": 1}
        ).sort("uploadTimestamp", -1).limit(3))
        
        for img in recent_uploads:
            img["_id"] = str(img["_id"])
            img["file_id"] = str(img["file_id"]) if "file_id" in img else None
            if "uploadTimestamp" in img:
                img["uploadTimestamp"] = img["uploadTimestamp"].isoformat()
            img["recommendation_reason"] = "Recently uploaded"
            if not any(rec["_id"] == img["_id"] for rec in recommendations):
                recommendations.append(img)
        
        # 4. Based on chat topics
        if top_topic_words:
            topic_pipeline = [
                {"$match": {"labels.label": {"$in": top_topic_words}}},
                {"$match": {"_id": {"$nin": [ObjectId(id) for id in viewed_image_ids]}}},
                {"$limit": 3}
            ]
            
            topic_images = list(mongo.db.images.aggregate(topic_pipeline))
            
            for img in topic_images:
                img["_id"] = str(img["_id"])
                img["file_id"] = str(img["file_id"]) if "file_id" in img else None
                if "uploadTimestamp" in img:
                    img["uploadTimestamp"] = img["uploadTimestamp"].isoformat()
                    
                matching_topics = []
                for topic in top_topic_words:
                    for label in img.get("labels", []):
                        if isinstance(label, dict) and "label" in label and topic in label["label"].lower():
                            matching_topics.append(topic)
                
                if matching_topics:
                    topics_str = ", ".join(matching_topics)
                    img["recommendation_reason"] = f"Matches your interests in {topics_str}"
                else:
                    img["recommendation_reason"] = "Based on your chat history"
                
                if not any(rec["_id"] == img["_id"] for rec in recommendations):
                    recommendations.append(img)
        
        recommendations = recommendations[:10]
        
        return jsonify({
            "recommendations": recommendations,
            "user_interests": top_topic_words if top_topic_words else ["No interests detected yet"],
            "common_labels": common_label_words if 'common_label_words' in locals() else ["No viewing history yet"]
        }), 200
        
    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "An error occurred generating recommendations", "details": str(e)}), 500

@app.route('/user/update', methods=['PUT'])
def update_user():
    """Update user information"""
    try:
        data = request.json
        user_id = data.get('user_id')
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        user = mongo.db.users.find_one({"_id": user_id})
        if not user:
            return jsonify({"error": "User not found"}), 404

        update_fields = {}
        if username:
            update_fields['username'] = username
        if email:
            update_fields['email'] = email
        if password:
            update_fields['password'] = hashlib.sha256(password.encode()).hexdigest()

        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400

        # Update the user
        result = mongo.db.users.update_one(
            {"_id": user_id},
            {"$set": update_fields}
        )

        if result.modified_count == 0:
            return jsonify({"error": "No changes made"}), 400

        return jsonify({
            "message": "User information updated successfully",
            "updated_fields": list(update_fields.keys())
        }), 200

    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({"error": "An error occurred while updating user information"}), 500

@app.route('/user/delete', methods=['DELETE'])
def delete_user():
    """Delete user account and associated data"""
    try:
        data = request.json
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        user = mongo.db.users.find_one({"_id": user_id})
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Delete user's images
        mongo.db.images.delete_many({"user_id": user_id})
        
        # Delete user's chat history
        mongo.db.chatHistory.delete_many({"user_id": user_id})
        
        # Delete user's uploads
        mongo.db.uploadsImage.delete_many({"user_id": user_id})
        
        # Delete user's image views
        mongo.db.imageViews.delete_many({"user_id": user_id})
        
        # Finally, delete the user
        result = mongo.db.users.delete_one({"_id": user_id})

        if result.deleted_count == 0:
            return jsonify({"error": "Failed to delete user"}), 500

        return jsonify({"message": "User account and all associated data deleted successfully"}), 200

    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({"error": "An error occurred while deleting user account"}), 500

@app.route('/test-db', methods=['GET'])
def test_db():
    """Test MongoDB connection and chat history collection"""
    try:
        mongo.db.command('ping')
        
        # Test chat history collection
        chat_count = mongo.db.chatHistory.count_documents({})
        image_count = mongo.db.images.count_documents({})
        
        return jsonify({
            "status": "success",
            "mongo_connected": True,
            "chat_history_count": chat_count,
            "images_count": image_count
        }), 200
        
    except Exception as e:
        print(f"Database test error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "mongo_connected": False,
            "error": str(e)
        }), 500

@app.route('/debug_image_labels/<image_id>', methods=['GET'])
def debug_image_labels(image_id):
    """Debug endpoint to check image labels and processing"""
    try:
        print(f"\n=== Debugging Image Labels ===")
        print(f"Image ID: {image_id}")
        
        if not ObjectId.is_valid(image_id):
            print("Invalid ObjectId format")
            return jsonify({"error": "Invalid image_id format"}), 400
            
        image_info = mongo.db.images.find_one({"_id": ObjectId(image_id)})
        if not image_info:
            print("Image not found in database")
            return jsonify({"error": "Image not found"}), 404
            
        print(f"Image found: {image_info.get('filename')}")
        print(f"Labels: {image_info.get('labels')}")
        print(f"Raw image info: {image_info}")
        
        return jsonify({
            "labels": image_info.get('labels'),
            "raw": image_info
        }), 200
    except Exception as e:
        print(f"Debug error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)