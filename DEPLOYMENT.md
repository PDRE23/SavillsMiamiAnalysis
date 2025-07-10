# Deploying to Streamlit Cloud

This guide will help you deploy your Savills Property Analyzer to Streamlit Cloud.

## Prerequisites

1. **GitHub Repository**: Your code must be in a public GitHub repository
2. **Streamlit Cloud Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)

## Step 1: Push to GitHub

If you haven't already, push your code to GitHub:

```bash
git add .
git commit -m "Add purchase analyzer functionality"
git push origin main
```

## Step 2: Deploy to Streamlit Cloud

1. **Go to [share.streamlit.io](https://share.streamlit.io)**
2. **Sign in** with your GitHub account
3. **Click "New app"**
4. **Configure your app**:
   - **Repository**: Select your GitHub repository
   - **Branch**: `main` (or your default branch)
   - **Main file path**: `app.py` (or `lease_analysis/app.py`)
   - **App URL**: Choose a custom URL (optional)

## Step 3: Configure App Settings

### Main File Path Options:
- **Option 1**: `app.py` (uses the root entry point)
- **Option 2**: `lease_analysis/app.py` (direct path to the app)

### Advanced Settings:
- **Python version**: 3.9+ (auto-detected)
- **Requirements file**: `requirements.txt` (auto-detected)

## Step 4: Deploy

Click "Deploy!" and wait for the build to complete.

## Troubleshooting

### Common Issues:

1. **Import Errors**: Make sure all dependencies are in `requirements.txt`
2. **File Not Found**: Ensure the main file path is correct
3. **Module Errors**: Check that all `__init__.py` files exist

### Debugging:

- Check the build logs in Streamlit Cloud
- Test locally first: `streamlit run app.py`
- Verify all imports work: `python -c "import lease_analysis.app"`

## Your App URL

Once deployed, your app will be available at:
`https://your-app-name-your-username.streamlit.app`

## Updates

To update your deployed app:
1. Make changes to your code
2. Push to GitHub: `git push origin main`
3. Streamlit Cloud will automatically redeploy

## Local Development

For local development, use:
```bash
streamlit run app.py
# or
streamlit run lease_analysis/app.py
```

## Configuration

The app uses `.streamlit/config.toml` for configuration. Key settings:
- Theme colors and styling
- Server settings
- Performance optimizations

## Support

If you encounter issues:
1. Check the Streamlit Cloud logs
2. Test locally first
3. Verify all dependencies are in `requirements.txt`
4. Ensure your GitHub repository is public 