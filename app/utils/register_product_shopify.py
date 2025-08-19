import time
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Shopify API credentials
SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")


def retry_post(post_func, max_retries=3, backoff=1):
    for attempt in range(max_retries):
        try:
            response = post_func()
            if response.status_code == 200:
                return response
            else:
                print(
                    f"⚠️ Attempt {attempt + 1} failed. Status: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Exception on attempt {attempt + 1}: {e}")
        time.sleep(backoff ** attempt)
    raise Exception("Max retries exceeded.")

# register_external_perfumes_in_shopify(perfumes)


def register_external_perfumes_in_shopify(perfumes):
    """
    Registers external perfumes in Shopify, sets their metafields, and adds them to a collection.

    Args:
        perfumes (list): List of perfume dictionaries.

    Returns:
        list: Updated list with assigned Shopify product IDs.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
    }

    product_create_mutation = """
    mutation CreateProductWithOptions($input: ProductInput!, $media: [CreateMediaInput!]) {
      productCreate(input: $input, media: $media) {
        product {
          id
          title
          options {
            id
            name
            optionValues {
              id
              name
            }
          }
          media(first: 10) {
            edges {
              node {
                ... on MediaImage {
                  id
                  image {
                    originalSrc
                    altText
                  }
                }
              }
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    metafields_set_mutation = """
    mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields {
          namespace
          key
          value
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    add_to_collection_mutation = """
    mutation addProductToCollection($collectionId: ID!, $productIds: [ID!]!) {
      collectionAddProducts(
        id: $collectionId,
        productIds: $productIds
      ) {
        collection {
          id
          title
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    product_variants_mutation = """
    mutation CreateProductVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkCreate(productId: $productId, strategy: REMOVE_STANDALONE_VARIANT, variants: $variants) {
        productVariants {
          id
          title
          selectedOptions {
            name
            value
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    # existing_product_names = get_all_product_names()
    existing_product_names = [name.lower() for name in get_all_product_names()]
    # print(len(existing_product_names))

    COLLECTION_ID = "gid://shopify/Collection/285522591849"
    updated_perfumes = []
    failed_perfumes = []

    scent_goal_images = {
        "improve mood": "https://cdn.shopify.com/s/files/1/0565/0880/9321/files/Improve-mood.png?v=1741550936",
        "smell unique": "https://cdn.shopify.com/s/files/1/0565/0880/9321/files/smell-unique.png?v=1741550936",
        "boost confidence": "https://cdn.shopify.com/s/files/1/0565/0880/9321/files/Boost-confidence.png?v=1741550936",
        "increase attraction": "https://cdn.shopify.com/s/files/1/0565/0880/9321/files/Increase-sensuality.png?v=1741550935"
    }

    for perfume in perfumes:
        try:
            if perfume["title"].lower() in existing_product_names:
                print(f"Product {perfume['title']} already exists in Shopify.")
                continue

            # Prepare media
            media = []
            for scent_goal in perfume.get("primary_scent_goal", []):
                if scent_goal in scent_goal_images:
                    media.append({
                        "mediaContentType": "IMAGE",
                        "originalSource": scent_goal_images[scent_goal],
                        "alt": scent_goal
                    })

            # Build product payload
            input_data = {
                "title": perfume["title"],
                "descriptionHtml": f"<p>{perfume['description']}</p>",
                "vendor": "Evoked",
                "productType": "Eau De Parfum",
                "status": "ACTIVE",
                "tags": perfume["scent_vibes"] + perfume["seasons"] + perfume["occasions"] + perfume["target_gender"],
                "productOptions": [
                    {
                        "name": "size",
                        "values": [{"name": "5ml"}, {"name": "50ml"}, {"name": "100ml"}]
                    }
                ],
            }

            # Create product
            payload = {
                "query": product_create_mutation,
                "variables": {"input": input_data, "media": media}
            }

            # response = requests.post(
            #     SHOPIFY_STORE_URL, headers=headers, json=payload, timeout=100)
            response = retry_post(lambda: requests.post(SHOPIFY_STORE_URL,
                                                        headers=headers, json=payload, timeout=100))
            result = response.json()
            print("📊 API Usage:", response.headers.get(
                "X-Shopify-Shop-Api-Call-Limit"))

            if "errors" in result:
                raise Exception(f"GraphQL Errors: {result['errors']}")

            product_data = result.get("data", {}).get("productCreate", {})
            if product_data.get("userErrors"):
                raise Exception(f"User Errors: {product_data['userErrors']}")

            product_id = product_data["product"]["id"]
            numeric_product_id = product_id.split("/")[-1]
            perfume["id"] = numeric_product_id

            updated_perfumes.append(numeric_product_id)

            # Create metafields
            metafields = [
                {"namespace": "custom", "key": "scent_goal", "type": "rich_text_field", "value": json.dumps({"type": "root", "children": [
                                                                                                            {"type": "paragraph", "children": [{"type": "text", "value": ", ".join(perfume.get("primary_scent_goal", []))}]}]}), "ownerId": product_id},
                {"namespace": "custom", "key": "top_notes_custom", "type": "rich_text_field", "value": json.dumps({"type": "root", "children": [
                                                                                                                  {"type": "paragraph", "children": [{"type": "text", "value": ", ".join(perfume.get("top_notes", []))}]}]}), "ownerId": product_id},
                {"namespace": "custom", "key": "middle_notes_custom", "type": "rich_text_field", "value": json.dumps({"type": "root", "children": [
                                                                                                                     {"type": "paragraph", "children": [{"type": "text", "value": ", ".join(perfume.get("middle_notes", []))}]}]}), "ownerId": product_id},
                {"namespace": "custom", "key": "bottom_notes_custom", "type": "rich_text_field", "value": json.dumps({"type": "root", "children": [
                                                                                                                     {"type": "paragraph", "children": [{"type": "text", "value": ", ".join(perfume.get("bottom_notes", []))}]}]}), "ownerId": product_id},
                {"namespace": "custom", "key": "scent_accords", "type": "rich_text_field", "value": json.dumps({"type": "root", "children": [
                                                                                                               {"type": "paragraph", "children": [{"type": "text", "value": ", ".join(perfume.get("scent_vibes", []))}]}]}), "ownerId": product_id},
                {"namespace": "custom", "key": "seasons_text_", "type": "rich_text_field", "value": json.dumps({"type": "root", "children": [
                                                                                                               {"type": "paragraph", "children": [{"type": "text", "value": ", ".join(perfume.get("seasons", []))}]}]}), "ownerId": product_id},
                {"namespace": "custom", "key": "occasions_text_", "type": "rich_text_field", "value": json.dumps({"type": "root", "children": [
                                                                                                                 {"type": "paragraph", "children": [{"type": "text", "value": ", ".join(perfume.get("occasions", []))}]}]}), "ownerId": product_id},
                {"namespace": "custom", "key": "smells_like_", "type": "list.single_line_text_field", "value": json.dumps(
                    list(filter(None, [perfume.get("inspired_by", ""), perfume.get("perfume_url", "")]))), "ownerId": product_id}
            ]

            metafield_payload = {
                "query": metafields_set_mutation, "variables": {"metafields": metafields}}
            metafield_response = requests.post(
                SHOPIFY_STORE_URL, headers=headers, json=metafield_payload, timeout=100)
            metafield_result = metafield_response.json()

            if "errors" in metafield_result:
                raise Exception(
                    f"Metafield Errors: {metafield_result['errors']}")
            elif metafield_result.get("data", {}).get("metafieldsSet", {}).get("userErrors"):
                raise Exception(
                    f"Metafield User Errors: {metafield_result['data']['metafieldsSet']['userErrors']}")
            else:
                print(
                    f"Successfully registered {perfume['title']} with metafields.")

            # Add product to collection
            collection_payload = {
                "query": add_to_collection_mutation,
                "variables": {"collectionId": COLLECTION_ID, "productIds": [product_id]}
            }
            # collection_response = requests.post(
            #     SHOPIFY_STORE_URL, headers=headers, json=collection_payload, timeout=100)
            collection_response = retry_post(lambda: requests.post(
                SHOPIFY_STORE_URL, headers=headers, json=collection_payload, timeout=100))
            collection_result = collection_response.json()

            if "errors" in collection_result:
                raise Exception(
                    f"Collection Errors: {collection_result['errors']}")
            elif collection_result.get("data", {}).get("collectionAddProducts", {}).get("userErrors"):
                raise Exception(
                    f"Collection User Errors: {collection_result['data']['collectionAddProducts']['userErrors']}")
            else:
                print(f"Added {perfume['title']} to collection.")

            # Create variants
            variants = []
            for size, price in zip(["5ml", "50ml", "100ml"], perfume.get("prices", ["10.00", "30.00", "50.00"])):
                variants.append({
                    "price": price,
                    "optionValues": [{"name": size, "optionName": "size"}],
                    "inventoryQuantities": [{
                        "locationId": "gid://shopify/Location/62591008873",
                        "availableQuantity": 100
                    }],
                })

            variant_payload = {
                "query": product_variants_mutation,
                "variables": {"productId": product_id, "variants": variants}
            }
            # variant_response = requests.post(
            #     SHOPIFY_STORE_URL, headers=headers, json=variant_payload, timeout=120)
            variant_response = retry_post(lambda: requests.post(
                SHOPIFY_STORE_URL, headers=headers, json=variant_payload, timeout=120))
            variant_result = variant_response.json()

            if "errors" in variant_result:
                raise Exception(f"Variant Errors: {variant_result['errors']}")
            elif variant_result.get("data", {}).get("productVariantsBulkCreate", {}).get("userErrors"):
                raise Exception(
                    f"Variant User Errors: {variant_result['data']['productVariantsBulkCreate']['userErrors']}")
            else:
                print(f"Created variants for {perfume['title']}.")

        except Exception as e:
            print(f"Failed to process {perfume.get('title', 'Unknown')}: {e}")
            failed_perfumes.append({
                "title": perfume.get('title', 'Unknown'),
                "error": str(e)
            })

    if failed_perfumes:
        print(f"\n🚨 {len(failed_perfumes)} products failed:")
        for f in failed_perfumes:
            print(f"❌ {f['title']}: {f['error']}")

    return updated_perfumes


def get_all_product_names():
    """
    Fetches all product names from the Shopify store using pagination, excluding specified names.

    Returns:
        list: List of product names in the format ["Product A", "Product B"].
    """
    excluded_products = [
        "Set Box 1 (3 x Perfume Bottles + 3 Sample bottles)",
        "Set Box 2 (2 x Perfume Bottles + 2 Sample bottles)",
        "Set Box 3 (1 x Perfume Bottle + 1 Sample bottle)",
        "Evoked Perfume Set"
    ]

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
    }

    all_product_names = []
    has_next_page = True
    cursor = None

    while has_next_page:
        # Build query with pagination using cursor
        if cursor:
            query = """
            query {
              products(first: 250, after: "%s") {
                edges {
                  node {
                    title
                  }
                  cursor
                }
                pageInfo {
                  hasNextPage
                }
              }
            }
            """ % cursor
        else:
            query = """
            query {
              products(first: 250) {
                edges {
                  node {
                    title
                  }
                  cursor
                }
                pageInfo {
                  hasNextPage
                }
              }
            }
            """

        try:
            payload = {"query": query}
            response = requests.post(
                SHOPIFY_STORE_URL, headers=headers, json=payload, timeout=100)
            result = response.json()

            if "errors" in result:
                print(f"Error fetching products: {result['errors']}")
                return all_product_names

            products = result.get("data", {}).get(
                "products", {}).get("edges", [])

            # Extract product names and add to our list
            for product in products:
                if product["node"]["title"] not in excluded_products:
                    all_product_names.append(product["node"]["title"])

            # Check if there are more pages
            page_info = result.get("data", {}).get(
                "products", {}).get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)

            # Get cursor for the next page
            if products and has_next_page:
                cursor = products[-1].get("cursor")
            else:
                has_next_page = False

        except Exception as e:
            print(f"Exception occurred while fetching product names: {e}")
            return all_product_names  # Return what we have so far

    return all_product_names

# def get_all_product_names():
#     """
#     Fetches all product names from the Shopify store, excluding specified names.

#     Returns:
#         list: List of product names in the format ["Product A", "Product B"].
#     """
#     excluded_products = [
#         "Set Box 1 (3 x Perfume Bottles + 3 Sample bottles)",
#         "Set Box 2 (2 x Perfume Bottles + 2 Sample bottles)",
#         "Set Box 3 (1 x Perfume Bottle + 1 Sample bottle)",
#         "Evoked Perfume Set"
#     ]

#     headers = {
#         "Content-Type": "application/json",
#         "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
#     }

#     query = """
#     query {
#       products(first: 250) {
#         edges {
#           node {
#             title
#           }
#         }
#       }
#     }
#     """

#     try:
#         payload = {"query": query}
#         response = requests.post(
#             SHOPIFY_STORE_URL, headers=headers, json=payload, timeout=100)
#         result = response.json()

#         if "errors" in result:
#             print(f"Error fetching products: {result['errors']}")
#             return []

#         products = result.get("data", {}).get("products", {}).get("edges", [])
#         product_names = [
#             product["node"]["title"]
#             for product in products
#             if product["node"]["title"] not in excluded_products
#         ]

#         # print(product_names, len(product_names))
#         return product_names

#     except Exception as e:
#         print(f"Exception occurred while fetching product names: {e}")
#         return []


# def get_product_ids_from_titles(titles):
#     """
#     Given a list of perfume titles, returns a list of corresponding Shopify product IDs
#     from the internal_products_title_id.json file.

#     Args:
#         titles (list): List of perfume titles (strings)

#     Returns:
#         list: List of matched product IDs
#     """
#     CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
#     JSON_PATH = os.path.join(CURRENT_DIR, "internal_products_title_id.json")

#     if os.path.exists(JSON_PATH):
#         with open(JSON_PATH, "r", encoding="utf-8") as f:
#             internal_product_map = json.load(f)
#     else:
#         internal_product_map = []

#     matched_ids = []

#     for title in titles:
#         match = next(
#             (item["id"] for item in internal_product_map if item["title"] == title), None)
#         if match:
#             matched_ids.append(match)

#     return matched_ids
