# JEE Gurukul Deployment Checklist

## Pre-Deployment Checklist

### ✅ Environment Setup
- [ ] Create `.env` file with all required variables
- [ ] Set `SECRET_KEY` to a secure random string
- [ ] Configure `GOOGLE_API_KEY` (Gemini)
- [ ] Set up Google OAuth credentials
- [ ] Configure Google Cloud Storage bucket
- [ ] Upload MMD files to GCS bucket
- [ ] Upload `dist_topic.json` to GCS bucket

### ✅ Code Quality
- [ ] All templates exist and are properly formatted
- [ ] JavaScript in `test.html` is error-free
- [ ] Database models are properly defined
- [ ] All API endpoints return proper responses
- [ ] Error handling is implemented
- [ ] Logging is configured

### ✅ Testing
- [ ] Run `python test_complete_app.py`
- [ ] Test user registration and login
- [ ] Test Google OAuth login
- [ ] Test question generation for all subjects
- [ ] Test test-taking flow end-to-end
- [ ] Test results display
- [ ] Test navigation between pages

### ✅ Security
- [ ] `.env` file is in `.gitignore`
- [ ] No hardcoded secrets in code
- [ ] HTTPS is configured for production
- [ ] OAuth redirect URIs are secure
- [ ] Database permissions are set correctly
- [ ] GCS bucket permissions are appropriate

## Platform-Specific Deployment

### Railway
1. Connect your GitHub repository
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

### Render
1. Connect your GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `gunicorn wsgi:app`
4. Configure environment variables

### Heroku
1. Install Heroku CLI
2. Create app: `heroku create your-app-name`
3. Set environment variables: `heroku config:set KEY=value`
4. Deploy: `git push heroku main`

### DigitalOcean App Platform
1. Connect your GitHub repository
2. Set environment variables
3. Configure build and run commands
4. Deploy

## Post-Deployment Checklist

### ✅ Functionality Testing
- [ ] Homepage loads correctly
- [ ] User registration works
- [ ] User login works (both email and Google OAuth)
- [ ] Dashboard displays correctly
- [ ] Subject selection works
- [ ] Topic selection works
- [ ] Test generation works for all subjects
- [ ] Test-taking interface works
- [ ] Answer submission works
- [ ] Results page displays correctly
- [ ] Navigation between pages works

### ✅ Performance Testing
- [ ] Page load times are acceptable (< 3 seconds)
- [ ] Question generation completes within 30 seconds
- [ ] Database queries are optimized
- [ ] Static assets are served efficiently

### ✅ Error Handling
- [ ] 404 errors are handled gracefully
- [ ] 500 errors are logged and handled
- [ ] API errors return proper status codes
- [ ] User-friendly error messages are displayed

### ✅ Monitoring
- [ ] Set up application monitoring (if available)
- [ ] Configure error logging
- [ ] Set up uptime monitoring
- [ ] Monitor API usage and costs

## Production Environment Variables

```bash
# Production settings
FLASK_ENV=production
FLASK_DEBUG=False
OAUTHLIB_INSECURE_TRANSPORT=0

# Update OAuth redirect URI
GOOGLE_REDIRECT_URI=https://your-domain.com/google-callback

# Use production database (if applicable)
SQLALCHEMY_DATABASE_URI=your-production-database-url
```

## Troubleshooting Common Issues

### Question Generation Fails
- Check Gemini API key and quota
- Verify GCS bucket and file permissions
- Check network connectivity

### OAuth Login Fails
- Verify redirect URI matches exactly
- Check client ID and secret
- Ensure Google+ API is enabled

### Database Errors
- Run `flask db upgrade` to create tables
- Check database connection string
- Verify database permissions

### Static Files Not Loading
- Check file paths in templates
- Verify static folder structure
- Check web server configuration

## Maintenance

### Regular Tasks
- [ ] Monitor API usage and costs
- [ ] Check application logs for errors
- [ ] Update dependencies regularly
- [ ] Backup database (if applicable)
- [ ] Monitor disk space and performance

### Updates
- [ ] Test updates in staging environment
- [ ] Update environment variables if needed
- [ ] Deploy during low-traffic periods
- [ ] Monitor for issues after deployment

## Support

If you encounter issues:
1. Check the logs for error messages
2. Run the test script: `python test_complete_app.py`
3. Verify all environment variables are set
4. Check the troubleshooting section above
5. Review the deployment platform's documentation

## Success Criteria

Your app is successfully deployed when:
- ✅ All pages load without errors
- ✅ Users can register and login
- ✅ Tests can be generated and taken
- ✅ Results are displayed correctly
- ✅ Navigation works smoothly
- ✅ No critical errors in logs
- ✅ Performance is acceptable

🎉 **Congratulations! Your JEE Gurukul app is now live and ready for students!** 