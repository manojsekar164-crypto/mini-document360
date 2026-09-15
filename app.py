"""
Mini Document360 - Flask Knowledge Base Application
A lightweight SaaS documentation portal for viewing, creating, searching, and categorizing articles with analytics.
Provides production-quality validation, category management, error handling, and data integrity safeguards.
"""

import json
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mini-document360-secret-key-2026')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Filepath for storing articles JSON data
ARTICLES_FILE = os.path.join(os.path.dirname(__file__), 'articles.json')


def ensure_articles_file():
    """
    Ensure that articles.json exists on disk.
    If missing, automatically initialize it with an empty array.
    """
    if not os.path.exists(ARTICLES_FILE):
        try:
            with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            app.logger.info(f"Created missing articles file: {ARTICLES_FILE}")
        except OSError as e:
            app.logger.error(f"Error creating {ARTICLES_FILE}: {e}")


def validate_article(article):
    """
    Validate that an article object is a valid dictionary with non-empty string fields for
    'title', 'category', and 'content' after trimming whitespace.
    """
    if not isinstance(article, dict):
        return False
    
    title = str(article.get('title', '')).strip()
    category = str(article.get('category', '')).strip()
    content = str(article.get('content', '')).strip()

    return bool(title and category and content)


def load_articles():
    """
    Load articles list from articles.json.
    - Automatically creates the file if missing.
    - Prevents application crashes if the file is empty, corrupted, or not a list.
    - Filters out malformed records to protect application stability.
    - Returns a list of valid article dictionaries.
    """
    ensure_articles_file()

    try:
        with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                # File exists but is empty (0 bytes); return empty list safely
                return []
            
            data = json.loads(content)
            
            # Ensure the root element is a JSON list
            if not isinstance(data, list):
                app.logger.warning(f"{ARTICLES_FILE} content is not a list. Defaulting to empty list.")
                return []
            
            # Filter and keep only valid article dictionaries passing validate_article
            valid_articles = [
                {
                    'title': str(item.get('title', '')).strip(),
                    'category': str(item.get('category', '')).strip(),
                    'content': str(item.get('content', '')).strip()
                }
                for item in data
                if validate_article(item)
            ]
            return valid_articles
            
    except (json.JSONDecodeError, OSError) as e:
        app.logger.error(f"Error reading {ARTICLES_FILE}: {e}")
        return []


def save_articles(articles):
    """
    Persist the given list of articles into articles.json.
    - Validates all articles prior to saving to prevent disk storage corruption.
    - Returns True on success, False if an error occurs.
    """
    if not isinstance(articles, list):
        app.logger.error("Attempted to save non-list articles data.")
        return False

    # Clean and validate all article records
    clean_articles = [
        {
            'title': str(item.get('title', '')).strip(),
            'category': str(item.get('category', '')).strip(),
            'content': str(item.get('content', '')).strip()
        }
        for item in articles
        if validate_article(item)
    ]

    try:
        with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(clean_articles, f, indent=2, ensure_ascii=False)
        return True
    except OSError as e:
        app.logger.error(f"Error writing to {ARTICLES_FILE}: {e}")
        return False


def get_analytics(articles):
    """
    Compute dynamic SaaS dashboard metrics from articles.json dataset:
    - total_articles: Total count of all valid article records stored.
    - total_categories: Count of unique, non-empty category names across all articles.
    """
    total_articles = len(articles)
    
    # Extract unique categories (ignoring empty or whitespace-only strings)
    unique_categories = set(
        article.get('category', '').strip()
        for article in articles
        if isinstance(article, dict) and article.get('category', '').strip()
    )
    total_categories = len(unique_categories)

    return {
        'total_articles': total_articles,
        'total_categories': total_categories
    }


def get_categories_list(articles):
    """
    Extract a sorted list of unique, non-empty category names from articles.
    """
    category_set = set()
    for article in articles:
        if isinstance(article, dict):
            cat = str(article.get('category', '')).strip()
            if cat:
                category_set.add(cat)
    return sorted(list(category_set), key=lambda s: s.lower())


@app.route('/')
def index():
    """
    Home page: Display dashboard analytics, category filters, search bar, and article cards.
    Calculates total articles and total categories dynamically from articles.json.
    """
    articles = load_articles()
    analytics = get_analytics(articles)
    categories = get_categories_list(articles)

    return render_template(
        'index.html', 
        articles=articles, 
        query='',
        active_category='',
        categories=categories,
        total_articles=analytics['total_articles'],
        total_categories=analytics['total_categories']
    )


@app.route('/category/<category_name>')
def filter_by_category(category_name):
    """
    Category Filter route:
    - Accepts a category_name path parameter.
    - Performs case-insensitive category filtering against all articles.
    - Displays active category pill indicator and renders matching articles.
    """
    category_name_clean = category_name.strip()
    all_articles = load_articles()
    analytics = get_analytics(all_articles)
    categories = get_categories_list(all_articles)

    # Filter articles matching the requested category name (case-insensitive)
    matching_articles = [
        article for article in all_articles
        if str(article.get('category', '')).strip().lower() == category_name_clean.lower()
    ]

    return render_template(
        'index.html',
        articles=matching_articles,
        query='',
        active_category=category_name_clean,
        categories=categories,
        total_articles=analytics['total_articles'],
        total_categories=analytics['total_categories']
    )


@app.route('/search', methods=['GET'])
def search():
    """
    Search route:
    - Accepts a 'q' query parameter from the homepage search bar.
    - Performs case-insensitive matching against title, category, and content.
    - Computes dashboard analytics and category list dynamically.
    - Renders index.html with the filtered articles.
    """
    query = request.args.get('q', '').strip()
    all_articles = load_articles()
    analytics = get_analytics(all_articles)
    categories = get_categories_list(all_articles)

    if not query:
        # If query is empty, return all articles
        return render_template(
            'index.html', 
            articles=all_articles, 
            query='',
            active_category='',
            categories=categories,
            total_articles=analytics['total_articles'],
            total_categories=analytics['total_categories']
        )

    query_lower = query.lower()
    matching_articles = []

    # Search logic: check title, category, and content case-insensitively
    for article in all_articles:
        title = str(article.get('title', '')).lower()
        category = str(article.get('category', '')).lower()
        content = str(article.get('content', '')).lower()

        if query_lower in title or query_lower in category or query_lower in content:
            matching_articles.append(article)

    return render_template(
        'index.html', 
        articles=matching_articles, 
        query=query,
        active_category='',
        categories=categories,
        total_articles=analytics['total_articles'],
        total_categories=analytics['total_categories']
    )


@app.route('/add', methods=['GET', 'POST'])
def add_article():
    """
    Add Article route:
    - GET: Render the form to create a new article.
    - POST: Validate form inputs (reject empty/whitespace-only values), save new article to articles.json,
            flash a success message, and redirect to homepage.
    """
    if request.method == 'POST':
        # Retrieve and trim form fields
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        content = request.form.get('content', '').strip()

        # Backend validation: reject empty or whitespace-only submissions
        errors = []
        if not title:
            errors.append("Article title is required.")
        if not category:
            errors.append("Category is required.")
        if not content:
            errors.append("Article content is required.")

        if errors:
            error_message = " ".join(errors)
            flash(error_message, 'danger')
            return render_template('add.html', error=error_message, title=title, category=category, content=content), 400

        new_article = {
            'title': title,
            'category': category,
            'content': content
        }

        # Load existing articles, append new validated article, and persist
        articles = load_articles()
        articles.append(new_article)
        
        if not save_articles(articles):
            error_message = "Failed to save the article due to a server error. Please try again."
            flash(error_message, 'danger')
            return render_template('add.html', error=error_message, title=title, category=category, content=content), 500

        # Flash success feedback and redirect to homepage
        flash(f'Article "{title}" created successfully!', 'success')
        return redirect(url_for('index'))

    # If GET request, render form template
    return render_template('add.html')


if __name__ == '__main__':
    # Ensure articles.json file is initialized if missing
    ensure_articles_file()
    # Run Flask development server
    app.run(debug=True, host='127.0.0.1', port=5000)





