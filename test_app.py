import json
import os
import unittest
import shutil
from app import app, ARTICLES_FILE, load_articles, save_articles, ensure_articles_file, get_analytics

class MiniDocument360TestCase(unittest.TestCase):

    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Backup existing articles.json if present
        self.backup_file = ARTICLES_FILE + '.backup'
        if os.path.exists(ARTICLES_FILE):
            shutil.copyfile(ARTICLES_FILE, self.backup_file)

        # Initialize test dataset
        self.test_articles = [
            {
                "title": "Getting Started with Document360",
                "category": "Onboarding",
                "content": "Welcome to Mini Document360! Platform details here."
            },
            {
                "title": "Best Practices for Technical Writing",
                "category": "Guidelines",
                "content": "Keep your documentation concise and use clear headings."
            },
            {
                "title": "API Documentation Overview",
                "category": "API",
                "content": "Document RESTful endpoints clearly with HTTP methods and status codes."
            }
        ]
        save_articles(self.test_articles)

    def tearDown(self):
        # Restore backup file if it existed
        if os.path.exists(self.backup_file):
            shutil.copyfile(self.backup_file, ARTICLES_FILE)
            if os.path.exists(self.backup_file):
                os.remove(self.backup_file)
        elif os.path.exists(ARTICLES_FILE):
            os.remove(ARTICLES_FILE)

    def test_tc1_home_page_loads(self):
        """Test Case 1: Home page loads successfully."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Mini Document360 Documentation", response.data)
        self.assertIn(b"Getting Started with Document360", response.data)

    def test_tc2_navigate_to_add(self):
        """Test Case 2: Navigate to /add."""
        response = self.client.get('/add')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Create New Article", response.data)

    def test_tc3_to_tc6_add_article_and_verify_persistence(self):
        """
        Test Case 3: Add article (Title: Login Issue, Category: Authentication, Content: User unable to login.)
        Test Case 4: Redirect to home page.
        Test Case 5: Verify article card appears.
        Test Case 6: Refresh application & verify article exists in articles.json.
        """
        payload = {
            'title': 'Login Issue',
            'category': 'Authentication',
            'content': 'User unable to login.'
        }
        response = self.client.post('/add', data=payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Test Case 5: Verify article card appears on home page
        self.assertIn(b"Login Issue", response.data)
        self.assertIn(b"Authentication", response.data)
        self.assertIn(b"User unable to login.", response.data)

        # Test Case 6: Reload articles directly from articles.json to verify persistence
        saved_articles = load_articles()
        matching = [a for a in saved_articles if a.get('title') == 'Login Issue']
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]['category'], 'Authentication')
        self.assertEqual(matching[0]['content'], 'User unable to login.')

    def test_phase3_search_functionality(self):
        """
        Phase 3 Testing:
        Search: login, api, authentication. Verify matching articles appear.
        Verify search against title, category, and content.
        Verify case-insensitivity.
        Verify no matching articles message.
        """
        # First add 'Login Issue' article
        self.client.post('/add', data={
            'title': 'Login Issue',
            'category': 'Authentication',
            'content': 'User unable to login.'
        })

        # Search 'login' (should match 'Login Issue' in title and content)
        res_login = self.client.get('/search?q=login')
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"Login Issue", res_login.data)

        # Search 'LOGIN' (case-insensitive test)
        res_login_upper = self.client.get('/search?q=LOGIN')
        self.assertEqual(res_login_upper.status_code, 200)
        self.assertIn(b"Login Issue", res_login_upper.data)

        # Search 'api' (should match 'API Documentation Overview')
        res_api = self.client.get('/search?q=api')
        self.assertEqual(res_api.status_code, 200)
        self.assertIn(b"API Documentation Overview", res_api.data)

        # Search 'authentication' (should match 'Authentication' category)
        res_auth = self.client.get('/search?q=authentication')
        self.assertEqual(res_auth.status_code, 200)
        self.assertIn(b"Login Issue", res_auth.data)

        # Search nonexistent term -> check 'No matching articles found.' message
        res_none = self.client.get('/search?q=xyznonexistent99')
        self.assertEqual(res_none.status_code, 200)
        self.assertIn(b"No matching articles found.", res_none.data)

    def test_phase4_analytics(self):
        """
        Phase 4 Testing:
        Verify Total Articles and Total Categories update dynamically.
        - Verify initial analytics counts.
        - Add article with new category -> verify both counts increment.
        - Add article with existing category -> verify article count increments, category count remains unchanged.
        """
        # Initial stats: 3 articles, 3 unique categories (Onboarding, Guidelines, API)
        res_initial = self.client.get('/')
        self.assertEqual(res_initial.status_code, 200)
        self.assertIn(b"Total Articles", res_initial.data)
        self.assertIn(b"Total Categories", res_initial.data)

        # Add article with a NEW category ("Security")
        self.client.post('/add', data={
            'title': '2FA Setup',
            'category': 'Security',
            'content': 'How to enable 2FA authentication.'
        })

        articles = load_articles()
        analytics = get_analytics(articles)
        self.assertEqual(analytics['total_articles'], 4)
        self.assertEqual(analytics['total_categories'], 4)

        # Add another article with an EXISTING category ("Security")
        self.client.post('/add', data={
            'title': 'Password Policy',
            'category': 'Security',
            'content': 'Password must be at least 12 characters.'
        })

        articles_after = load_articles()
        analytics_after = get_analytics(articles_after)
        self.assertEqual(analytics_after['total_articles'], 5)
        self.assertEqual(analytics_after['total_categories'], 4)

    def test_empty_form_submission_rejected(self):
        """Verify empty and whitespace-only submissions are blocked with 400 Bad Request."""
        # Case A: Entirely empty form fields
        res_empty = self.client.post('/add', data={'title': '', 'category': '', 'content': ''})
        self.assertEqual(res_empty.status_code, 400)
        self.assertIn(b"Article title is required", res_empty.data)

        # Case B: Whitespace only fields
        res_spaces = self.client.post('/add', data={'title': '   ', 'category': '   ', 'content': '   '})
        self.assertEqual(res_spaces.status_code, 400)
        self.assertIn(b"Article title is required", res_spaces.data)

    def test_category_filtering(self):
        """Verify Category Management route /category/<category_name>."""
        # Query /category/API -> should match 'API Documentation Overview'
        res_cat_api = self.client.get('/category/API')
        self.assertEqual(res_cat_api.status_code, 200)
        self.assertIn(b"API Documentation Overview", res_cat_api.data)
        self.assertNotIn(b"Getting Started with Document360", res_cat_api.data)

        # Case-insensitive category query /category/onboarding
        res_cat_onboarding = self.client.get('/category/onboarding')
        self.assertEqual(res_cat_onboarding.status_code, 200)
        self.assertIn(b"Getting Started with Document360", res_cat_onboarding.data)

    def test_auto_creation_when_missing(self):
        """Requirement 13: Ensure articles.json is automatically created if missing."""
        if os.path.exists(ARTICLES_FILE):
            os.remove(ARTICLES_FILE)
        self.assertFalse(os.path.exists(ARTICLES_FILE))
        
        articles = load_articles()
        self.assertEqual(articles, [])
        self.assertTrue(os.path.exists(ARTICLES_FILE))

    def test_empty_and_corrupted_articles_json(self):
        """Requirement 14: Prevent application crashes if articles.json is empty or corrupted."""
        # Case A: 0-byte file
        with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        articles = load_articles()
        self.assertEqual(articles, [])
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)

        # Case B: Corrupted JSON
        with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
            f.write('{ malformed json ...')
        articles = load_articles()
        self.assertEqual(articles, [])
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)

        # Case C: Valid JSON but not a list (e.g. dictionary)
        with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
            f.write('{"key": "value"}')
        articles = load_articles()
        self.assertEqual(articles, [])
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
