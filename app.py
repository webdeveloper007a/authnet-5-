from flask import Flask, request, jsonify
from stripe_processor import StripeProcessor
import logging
import os

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize StripeProcessor
processor = StripeProcessor()

@app.route('/gateway=authnet5$/cc=<cc_details>', methods=['GET'])
def process_card(cc_details):
    """
    Endpoint to process card details using StripeProcessor.
    Returns the direct response from process_card_at.
    Expects card details in the format: number|mm|yy|cvc
    """
    try:
        if not cc_details:
            logger.error("No card details provided")
            return jsonify({
                "status": "Declined",
                "response": "Invalid card format",
                "gateway": "Authnet [5$]"
            }), 400

        # Process the card and return the direct response
        result = processor.process_card_at(cc_details)
        logger.info(f"Card processing result: {result}")
        status_code = 200 if result['status'] == 'Approved' else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Error processing card: {str(e)}")
        return jsonify({
            "status": "Declined",
            "response": f"Processing Failed: {str(e)}",
            "gateway": "Authnet [5$]"
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "Declined",
        "response": "Endpoint not found",
        "gateway": "Authnet [5$]"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "status": "Declined",
        "response": "Method not allowed",
        "gateway": "Authnet [5$]"
    }), 405

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
