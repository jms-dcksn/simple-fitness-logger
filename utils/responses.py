from flask import jsonify

def api_response(data=None, message=None, status=200):
    response = {
        'success': 200 <= status < 300,
        'data': data,
        'message': message
    }
    return jsonify(response), status

def error_response(message, status=400):
    return api_response(message=message, status=status)