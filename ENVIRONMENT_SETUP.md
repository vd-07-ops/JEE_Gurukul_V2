# Environment Setup Guide for JEE Gurukul

## Required Environment Variables

Create a `.env` file in your project root with the following variables:

```bash
# Flask Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=development
FLASK_DEBUG=True

# Google API Configuration
GOOGLE_API_KEY=your-gemini-api-key-here
GOOGLE_CLIENT_ID=your-google-oauth-client-id-here
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:5000/google-callback

# Google Cloud Storage Configuration
GOOGLE_CLOUD_PROJECT=your-gcp-project-id-here
GCS_BUCKET_NAME=your-gcs-bucket-name-here

# Database Configuration (SQLite for development)
SQLALCHEMY_DATABASE_URI=sqlite:///jee_gurukul.db
SQLALCHEMY_TRACK_MODIFICATIONS=False

# OAuth Configuration (for local development)
OAUTHLIB_INSECURE_TRANSPORT=1
```

## How to Get These Values

### 1. SECRET_KEY
Generate a secure secret key:
```python
import secrets
print(secrets.token_hex(32))
```

### 2. GOOGLE_API_KEY (Gemini)
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your .env file

### 3. Google OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Set application type to "Web application"
6. Add authorized redirect URIs:
   - `http://localhost:5000/google-callback` (for development)
   - `https://your-domain.com/google-callback` (for production)
7. Copy Client ID and Client Secret to your .env file

### 4. Google Cloud Storage
1. In Google Cloud Console, enable Cloud Storage API
2. Create a bucket or use existing one
3. Upload your MMD files to `md_files/` folder:
   - `md_files/math.mmd`
   - `md_files/physics.mmd`
   - `md_files/chemistry.mmd`
4. Upload `static/dist_topic.json` to your bucket
5. Set bucket permissions to allow read access

### 5. Google Cloud Project ID
Your project ID is visible in the Google Cloud Console URL or project settings.

## Production Settings

For production deployment, update these values:

```bash
FLASK_ENV=production
FLASK_DEBUG=False
OAUTHLIB_INSECURE_TRANSPORT=0
GOOGLE_REDIRECT_URI=https://your-domain.com/google-callback
```

## Testing Your Setup

Run the test script to verify everything is working:

```bash
python test_app_integration.py
```

## Troubleshooting

### Common Issues:

1. **"GOOGLE_API_KEY not found"**
   - Check your .env file exists and has the correct variable name
   - Ensure no extra spaces or quotes around the value

2. **"GCS_BUCKET_NAME environment variable not set"**
   - Verify your bucket name is correct
   - Check bucket permissions

3. **OAuth errors**
   - Verify redirect URI matches exactly
   - Check client ID and secret are correct
   - Ensure Google+ API is enabled

4. **Database errors**
   - Run `flask db upgrade` to create tables
   - Check database file permissions

## Security Notes

- Never commit your .env file to version control
- Use strong, unique secret keys
- Regularly rotate API keys
- Use HTTPS in production
- Set appropriate bucket permissions 