from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import uuid
import requests

load_dotenv()

app = Flask(__name__)
CORS(app)  

# Load config from .env
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET = os.getenv('S3_BUCKET_NAME')

# Initialize S3 client
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    endpoint_url=f'https://s3.{AWS_REGION}.amazonaws.com' 
)


# --- API 1: Upload file to S3 ---
@app.route('/upload', methods=['POST'])
def upload_file():
    print("📥 Received upload request")

    if 'file' not in request.files:
        print("❌ No file part in the request")
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    print(f"🔍 File field received: {file.filename}")

    if file.filename == '':
        print("❌ No file selected")
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    print(f"📝 Secure filename: {filename}")
    print(f"🔑 Unique filename: {unique_filename}")

    try:
        s3_client.upload_fileobj(file, S3_BUCKET, unique_filename)
        print(f"✅ File uploaded to S3: {unique_filename}")
        return jsonify({'message': 'File uploaded', 'filename': unique_filename}), 200
    except Exception as e:
        print(f"💥 Error uploading file to S3: {str(e)}")
        return jsonify({'error': str(e)}), 500


# --- API 2: Generate Shareable Link ---
@app.route('/share/<filename>', methods=['GET'])
def generate_shareable_link(filename):
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': filename},
            ExpiresIn=300  # Link valid for 5 minutes
        )
        return jsonify({'shareable_link': presigned_url}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/', methods=['GET'])
def home():
    return "Cloud File Sharing App is running 🚀", 200

# --- New API: Proxy to Job Search App's Resume Match API ---
@app.route('/analyze-resume', methods=['POST'])
def analyze_resume_text():
    """
    Accepts raw resume text and sends it to the Job Search App's
    /api/resume-match API to get recommended roles.
    """
    try:
        data = request.get_json()
        resume_text = data.get('resume', '')

        if not resume_text.strip():
            return jsonify({'error': 'Resume text is empty'}), 400

        # Forward to Job Search App
        job_api_url = 'https://scp-backend-m0uu.onrender.com/api/resume-match'
        response = requests.post(job_api_url, json={'resume': resume_text})

        return jsonify(response.json()), response.status_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
