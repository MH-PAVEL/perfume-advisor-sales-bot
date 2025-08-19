from flask import request, jsonify

from bson import ObjectId
import re

from flask import current_app as app
db = app.db

# Email validation function


def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

# Generic function to update email in a given collection


def update_email_in_collection(doc_id, collection):
    try:
        data = request.json
        email = data.get("email")

        if not email or not is_valid_email(email):
            return jsonify({"error": "A valid email is required"}), 400

        obj_id = ObjectId(doc_id)
        result = collection.update_one(
            {"_id": obj_id}, {"$set": {"email": email}})

        if result.matched_count == 0:
            return jsonify({"error": "Document not found"}), 404

        return jsonify({"message": "Email updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
