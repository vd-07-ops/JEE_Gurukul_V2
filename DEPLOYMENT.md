# JEE Gurukul - Deployment Guide

## 🚀 Production Deployment Options

### Option 1: Railway (Recommended - Free & Easy)
1. **Sign up** at [railway.app](https://railway.app)
2. **Connect your GitHub** repository
3. **Deploy automatically** - Railway will detect the Python app
4. **Set environment variables** in Railway dashboard:
   ```
   GOOGLE_API_KEY=your_gemini_api_key
   GOOGLE_CLIENT_ID=your_google_oauth_client_id
   GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
   GOOGLE_REDIRECT_URI=https://your-app-name.railway.app/google-callback
   GOOGLE_CLOUD_PROJECT=your_gcp_project_id
   GCS_BUCKET_NAME=jee_gurukul
   SECRET_KEY=your_secret_key_here
   ```
5. **Your app will be live** at `https://your-app-name.railway.app`

### Option 2: Render (Free Tier Available)
1. **Sign up** at [render.com](https://render.com)
2. **Create new Web Service**
3. **Connect your GitHub** repository
4. **Configure**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment**: Python 3
5. **Set environment variables** (same as above)
6. **Deploy** - Your app will be live at `https://your-app-name.onrender.com`

### Option 3: Heroku (Paid)
1. **Sign up** at [heroku.com](https://heroku.com)
2. **Install Heroku CLI**
3. **Deploy**:
   ```bash
   heroku create your-app-name
   git push heroku main
   heroku config:set GOOGLE_API_KEY=your_key
   # Set other environment variables
   heroku open
   ```

### Option 4: Google Cloud Run (Free Tier)
1. **Enable Cloud Run** in Google Cloud Console
2. **Build and deploy**:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/jee-gurukul
   gcloud run deploy --image gcr.io/PROJECT_ID/jee-gurukul --platform managed
   ```

## 🔧 Environment Variables Setup

### Required Environment Variables:
```bash
# Google Gemini API
GOOGLE_API_KEY=your_gemini_api_key_here

# Google OAuth (for login)
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_REDIRECT_URI=https://your-domain.com/google-callback

# Google Cloud Storage
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
GCS_BUCKET_NAME=jee_gurukul

# Flask Security
SECRET_KEY=your_random_secret_key_here
```

### How to Get These Keys:

#### 1. Google Gemini API Key:
- Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
- Create a new API key
- Copy the key

#### 2. Google OAuth Credentials:
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Navigate to "APIs & Services" > "Credentials"
- Create OAuth 2.0 Client ID
- Add your domain to authorized redirect URIs

#### 3. Google Cloud Storage:
- Ensure your GCS bucket `jee_gurukul` is accessible
- Verify all required files are present:
  - `static/dist_topic.json`
  - `static/original_questions.json`
  - `md_files/math.mmd`
  - `md_files/physics.mmd`
  - `md_files/chemistry.mmd`
  - `vector_db/math_documents.pkl`
  - `vector_db/physics_documents.pkl`
  - `vector_db/chemistry_documents.pkl`

## 📁 File Structure for Deployment

Ensure your repository has these files:
```
JEE-Gurukul/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # For Heroku/Railway
├── runtime.txt           # Python version
├── wsgi.py              # WSGI entry point
├── .env                  # Local environment variables (don't commit)
├── templates/            # HTML templates
├── static/              # CSS, JS, images
└── DEPLOYMENT.md        # This file
```

## 🧪 Testing Before Deployment

### 1. Local Testing:
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_API_KEY=your_key
export GOOGLE_CLIENT_ID=your_client_id
# ... set other variables

# Run locally
python app.py
```

### 2. Test Question Generation:
Visit: `http://localhost:5000/test-question-generation`

Should return:
```json
{
  "status": "success",
  "message": "Question generation is working correctly!",
  "question": {
    "subject": "math",
    "topic": "algebra",
    "question": "...",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct_answer": "A) ...",
    "step_by_step_solution": "...",
    "relevant_content": "..."
  }
}
```

## 🚀 Post-Deployment Checklist

### ✅ Verify These Work:
1. **Homepage loads** without errors
2. **User registration/login** works
3. **Subject selection** shows topics from GCS
4. **Question generation** works for all subjects
5. **Test taking** and scoring works
6. **Google OAuth** login works
7. **Database** stores user data correctly

### 🔍 Common Issues & Solutions:

#### Issue: "GOOGLE_API_KEY not found"
**Solution**: Set the environment variable in your deployment platform

#### Issue: "MMD file not found"
**Solution**: Verify all MMD files are in your GCS bucket under `md_files/`

#### Issue: "Topic distribution not found"
**Solution**: Ensure `static/dist_topic.json` exists in your GCS bucket

#### Issue: "Database errors"
**Solution**: The app will auto-create the database on first run

## 🌐 Custom Domain Setup (Optional)

### For Railway:
1. Go to your app settings
2. Add custom domain
3. Update DNS records
4. Update `GOOGLE_REDIRECT_URI` to use your domain

### For Render:
1. Go to app settings
2. Add custom domain
3. Configure DNS
4. Update environment variables

## 📊 Monitoring & Analytics

### Add to your app for production monitoring:
```python
# In app.py
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/jee_gurukul.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('JEE Gurukul startup')
```

## 🎉 Success!

Once deployed, your JEE Gurukul app will be live and accessible to students worldwide! 

### Features Available:
- ✅ User registration and login
- ✅ Google OAuth integration
- ✅ JEE-level question generation using MMD content
- ✅ Multiple subjects (Math, Physics, Chemistry)
- ✅ Topic-based question generation
- ✅ Test taking and scoring
- ✅ Detailed solutions and explanations
- ✅ Concept clarity explanations
- ✅ Test history tracking

### Next Steps:
1. **Monitor** the app for any issues
2. **Gather user feedback**
3. **Add more features** as needed
4. **Scale** if user base grows

---

**🎯 Your JEE Gurukul app is now ready for the world!** 🚀 