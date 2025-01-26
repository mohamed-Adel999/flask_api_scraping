from flask import Flask, request, jsonify
import requests
import time
import random
from bs4 import BeautifulSoup
import re
import json

app = Flask(__name__)

headers = {
    "authority": "www.amazon.eg",
    "user-agent": "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36",
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding':'gzip, deflate, br',
    'Accept-Language':'en-US,en;q=0.9',
    'Cache-Control':'max-age=0',
    'Cookie':'session-id=261-7433691-2773124; session-id-time=2082787201l; i18n-prefs=EGP; lc-acbeg=en_AE; ubid-acbeg=262-5246650-3905409; session-token=KpQ28aOazMUgerXMhYpMD66iEFYbfGXKgSs/ZOOZNJ2PUKVtH5FjrCCry+7mLeqJiVenNX/EKTX36X/d7TsZ8hpima5nSg3xbNELqHDh2c9e7dkT/83TbenKR2CIzCmygq57ZG6lI2eFUnVaQGoN+wgnuOBk0DPd9XEGJ8sRcyp4MY9mRBMAB1pIqQFvggezuaNWivGCx3ji25pWYeuDuORpD0Z4aPwfpY7msAY5M9mClg5uFOHUjrFmfZ3r4X0aGXdOJIZ9pM2Of+L3ZKDRxAlfNU1sSWGky8c9jzSkzPgYpk/ZJLeWMGRwr6uqtc4llLEP/B57AMFBREgc6kpwtychANaNlfxJ; csm-hit=s-5J2HQ2PEZDKNGN4BH6E3|1730237818862',
    'Device-Memory':'8',
    'Downlink':'10',
    'Dpr':'1',
    'Ect':'4g',
    'Rtt':'100',
    'Sec-Ch-Device-Memory':'8',
    'Sec-Ch-Dpr':'1',
    'Sec-Ch-Ua':'"Chromium";v="118", "Opera GX";v="104", "Not=A?Brand";v="99"',
    'Sec-Ch-Ua-Mobile':'?0',
    'Sec-Ch-Ua-Platform':'"Windows"',
    'Sec-Ch-Ua-Platform-Version':'"15.0.0"',
    'Sec-Ch-Viewport-Width':'921',
    'Sec-Fetch-Dest':'document',
    'Sec-Fetch-Mode':'navigate',
    'Sec-Fetch-Site':'same-origin',
    'Sec-Fetch-User':'?1',
    'Upgrade-Insecure-Requests':'1',
    'Viewport-Width':'921',
}

def GetCountry(text):
    pattern = r"in (.*?) on"
    gette = re.search(pattern, text)
    if gette:
        return gette.group(1)
    else:
        return "Not Found"

def fetch_data_with_retries(url, retries=50, backoff_factor=1, headersx=headers):
    session = requests.Session()
    for i in range(retries):
        try:
            response = session.get(url, headers=headersx)
            if response.status_code == 200:
                return response
            elif response.status_code == 503 or response.status_code == 404:
                delay = backoff_factor ** i + random.uniform(0, 1)
                time.sleep(delay)
            else:
                return response
        except requests.exceptions.RequestException as e:
            return None
    return None

def fetch_all_reviews(response):
    reviews = []
    if response:
        soupy = BeautifulSoup(response.text, 'html.parser')
        commintsicshns = soupy.find_all("div", class_=['a-section celwidget'])
        for commintsicshn in commintsicshns:
            try:
                profile_link_name = commintsicshn.find("a", class_=['a-profile'])
                user_ID = profile_link_name['href'].split('/')[5].split('.')[2] if profile_link_name else None
                name = profile_link_name.text if profile_link_name else commintsicshn.find("span", class_=['a-profile-name']).text

                rate = commintsicshn.find("span", class_=['a-icon-alt'])
                rate_text = rate.text.split(' ')[0] if rate else None

                title_and_content_review = commintsicshn.find_all("span", class_=False) or commintsicshn.find_all("span", class_=['cr-original-review-content'])
                title = title_and_content_review[0].text if title_and_content_review else None

                country_and_time = commintsicshn.find("span", class_=['a-size-base a-color-secondary review-date'])
                country = GetCountry(country_and_time.text) if country_and_time else None
                time = country_and_time.text.split(' ')[-3:] if country_and_time else None

                verified_purchase = commintsicshn.find("span", class_=['a-size-mini a-color-state a-text-bold'])
                verified = verified_purchase.text == "Verified Purchase" or verified_purchase.text == "عملية شراء معتمدة" if verified_purchase else False

                content_review = title_and_content_review[1].text if len(title_and_content_review) > 1 else None

                found_this_helpful = commintsicshn.find("span", class_=['a-size-base a-color-tertiary cr-vote-text'])
                helpful_count = found_this_helpful.text.split(' ')[0] if found_this_helpful else '0'

                reviews.append({
                    'user_ID': user_ID,
                    'name': name,
                    'rate': rate_text,
                    'title': title,
                    'country': country,
                    'time': time,
                    'verified_purchase': verified,
                    'content_review': content_review,
                    'helpful_count': helpful_count
                })
            except Exception as e:
                print(f"Error parsing review: {e}")
    return reviews

@app.route('/search', methods=['GET'])
def search_amazon():
    search_query = request.args.get('query')
    if not search_query:
        return jsonify({"error": "Query parameter is required"}), 400

    url = f"https://www.amazon.eg/-/en/s?k={search_query.replace(' ', '+')}"
    response = fetch_data_with_retries(url)
    if not response or response.status_code != 200:
        return jsonify({"error": "Failed to fetch data from Amazon"}), 500

    search_results = BeautifulSoup(response.text, 'html.parser')
    review_part = search_results.find_all('div', {"data-cy": "reviews-block"})
    number_of_reviews_and_their_links_for_results = [x.find('a', class_=['a-link-normal s-underline-text s-underline-link-text s-link-style']) for x in review_part]

    products = []
    for Review in number_of_reviews_and_their_links_for_results[:11]:
        link_of_product = Review['href']
        product_response = fetch_data_with_retries(f'https://www.amazon.eg{link_of_product}')
        if product_response:
            product_html = BeautifulSoup(product_response.text, 'html.parser')
            p_title = product_html.find("span", id=['productTitle'])
            price = product_html.find_all("span", class_=['aok-offscreen'])
            seller = product_html.find_all("span", class_=['a-size-small offer-display-feature-text-message'])
            rating = product_html.find_all("span", class_=['a-size-base a-color-base'])
            number_of_rating = product_html.find("span", id=['acrCustomerReviewText'])

            script_tag = product_html.find("div", id="imageBlock_feature_div").find_all("script", type="text/javascript")[1]
            script_content = script_tag.string if script_tag else ""
            match = re.search(r"var data = ({.*?});", script_content, re.DOTALL)
            image_links = []
            if match:
                data_content = match.group(1)
                cleaned_data = data_content.replace("'", '"')
                cleaned_data = re.sub(r",\s*}", "}", cleaned_data)
                cleaned_data = re.sub(r",\s*]", "]", cleaned_data)
                lines = cleaned_data.strip().split("\n")
                remaining_lines = lines[:5]
                remaining_lines[-1] = remaining_lines[-1][:-1]
                result = "\n".join(remaining_lines) + "\n}"
                try:
                    data_dict = json.loads(result)
                    image_links = data_dict['colorImages']['initial']
                except json.JSONDecodeError as e:
                    print(f"JSON error: {e}")

            products.append({
                'title': p_title.text if p_title else None,
                'price': price[0].text if price else None,
                'seller': seller[1].text if seller and len(seller) > 1 else None,
                'rating': rating[1].text if rating and len(rating) > 1 else None,
                'number_of_rating': number_of_rating.text if number_of_rating else None,
                'image_links': image_links,
                'reviews': fetch_all_reviews(product_response)
            })

    return jsonify(products)

if __name__ == '__main__':
    app.run()
