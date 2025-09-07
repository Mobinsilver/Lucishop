#!/usr/bin/env python3
"""
Simple test to check if admin_panel methods exist
"""

import os

# Set environment variables
os.environ["BOT_TOKEN"] = "8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE"
os.environ["OWNER_ID"] = "5803428693"
os.environ["BOT_USERNAME"] = "Crypto_navasan_bot"

try:
    import admin_panel
    
    # Create instance
    panel = admin_panel.AdminPanel()
    
    # Check methods
    methods_to_check = [
        'broadcast_message_start',
        'broadcast_forward_process',
        'capture_broadcast_message',
        'handle_admin_panel_text',
        'admin_panel_main'
    ]
    
    print("Checking admin panel methods:")
    for method in methods_to_check:
        if hasattr(panel, method):
            print(f"✅ {method} - EXISTS")
        else:
            print(f"❌ {method} - MISSING")
    
    print("\nAll methods checked!")
    
except Exception as e:
    print(f"Error: {e}")
