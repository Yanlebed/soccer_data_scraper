# lambda_layer/setup.py
# This creates a Playwright Lambda Layer
import os
import subprocess
import shutil


def create_playwright_layer():
    # Create directory structure
    os.makedirs('python/lib/python3.12/site-packages', exist_ok=True)

    # Install dependencies to the correct directory
    subprocess.run([
        'pip', 'install',
        'playwright', 'gspread', 'google-auth', 'gspread-dataframe',
        '-t', 'python/lib/python3.12/site-packages'
    ])

    # Install Playwright browsers
    subprocess.run([
        'python/lib/python3.9/site-packages/playwright/__main__.py',
        'install', 'chromium', '--with-deps'
    ])

    # Create zip file
    shutil.make_archive('playwright_layer', 'zip', '.', 'python')


if __name__ == "__main__":
    create_playwright_layer()