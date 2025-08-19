from datetime import datetime
from app.utils.landing_page_ai import delete_perfumes_from_pinecone
from app.utils.register_product_shopify import register_external_perfumes_in_shopify
from app.utils.functions import upsert_perfume_data
from concurrent.futures import ThreadPoolExecutor
# from bson import ObjectId
import logging
import time
from flask import current_app as app
db = app.db


# def background_processing_for_landing_page(filtered_perfumes_external_context_data, user_prompt, goals, perfume_no, recommendations, selected_perfumes):
#     """Runs Shopify & Pinecone operations in the background after sending response"""
#     try:

#     except Exception as e:
#         print(f"Background Processing Error: {e}")

# def register_external_perfumes_background(filtered_perfumes_external_context_data):
#     """ Function to run register_external_perfumes_in_shopify in the background with error handling """
#     try:
#         register_external_perfumes_in_shopify(
#             filtered_perfumes_external_context_data)
#     except Exception as e:
#         # Log the error
#         print(f"Error in register_external_perfumes_in_shopify: {e}")

# Configure logging to track background tasks
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


def register_external_perfumes_background(filtered_perfumes_external_context_data):
    """Function to register external perfumes in Shopify in the background with retries."""
    try:
        if not filtered_perfumes_external_context_data:
            logging.warning("No external perfumes to register.")
            return

        logging.info(
            f"Starting background process for {len(filtered_perfumes_external_context_data)} perfumes.")

        # Retry logic in case of failures
        max_retries = 3
        for attempt in range(max_retries):
            try:
                register_external_perfumes_in_shopify(
                    filtered_perfumes_external_context_data)
                logging.info("Successfully registered all external perfumes.")
                return  # Exit after successful execution
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(2)  # Short delay before retrying

        logging.critical(
            "Failed to register external perfumes after multiple attempts.")

    except Exception as e:
        logging.exception(
            f"Unexpected error in background perfume registration: {e}")


def background_processing_for_home_page(filtered_perfumes_external_context_data):
    """Background task to handle Shopify, Pinecone, and explanation_of_perfumes after sending response"""
    try:
        # Step 1: Handle external perfumes (Shopify & VectorDB)
        if len(filtered_perfumes_external_context_data) > 0:
            with ThreadPoolExecutor() as executor:
                # Register external perfumes in Shopify
                future_register = executor.submit(
                    register_external_perfumes_in_shopify, filtered_perfumes_external_context_data)

                # Remove external perfumes from Pinecone
                future_delete = executor.submit(
                    delete_perfumes_from_pinecone, filtered_perfumes_external_context_data)

                # Get the registered perfumes after Shopify API completes
                external_to_internal_perfumes = future_register.result()

                # Upsert the new external perfumes into internal vectorDB
                future_upsert = executor.submit(
                    upsert_perfume_data, external_to_internal_perfumes)

                # Ensure deletion is completed before upsert
                future_delete.result()
                future_upsert.result()

    except Exception as e:
        print(f"Background Processing Error: {e}")
