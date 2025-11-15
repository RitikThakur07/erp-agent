"""
Quick test script to verify Gemini integration
Run this to test if your Gemini API key is working
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini():
    """Test Gemini API connection"""
    
    print("🔍 Testing Gemini Integration...")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env file")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Try importing the library
    try:
        import google.generativeai as genai
        print("✅ google-generativeai library imported successfully")
    except ImportError:
        print("❌ google-generativeai not installed")
        print("   Run: pip install google-generativeai")
        return False
    
    # Configure and test API
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        print("✅ Gemini model initialized")
        
        # Test simple generation
        print("\n🧪 Testing generation...")
        response = model.generate_content("Say 'Hello from Gemini!' in a friendly way.")
        print(f"✅ Response received: {response.text[:100]}...")
        
        print("\n" + "=" * 50)
        print("🎉 Gemini integration is working perfectly!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"❌ Error testing Gemini: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_gemini()
    
    if success:
        print("\n✅ You're ready to run the ERP Builder!")
        print("   Run: python main.py")
        print("   Then open: http://localhost:8000")
    else:
        print("\n❌ Please fix the issues above before running the application")
