#!/usr/bin/env python3
"""
Test-Skript um /import Command direkt zu testen
"""

import sys
sys.path.insert(0, '.')

from src.web_import import WebImporter

# Test Import
importer = WebImporter()
print("Testing import of https://crowdcompany.info...")

success, message = importer.import_url(
    user_id=7043093505,
    url='https://crowdcompany.info',
    custom_filename='crowdcompany_test'
)

if success:
    print("\n✓ SUCCESS:")
    print(message)
else:
    print("\n✗ ERROR:")
    print(message)
