import telebot
import re
import os
import tempfile
import traceback
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Bot token
BOT_TOKEN = ""
bot = telebot.TeleBot(BOT_TOKEN)

# Store user states and data
user_states = {}
user_configs = {}

# Template files content
TEMPLATES = {
    'naira': 'nairabot_template.py',
    'ton': 'tonbot_template.py',
    'star': 'starbot_template.py'
}

def extract_config_from_message(message_text):
    """Extract configuration dictionary from the forwarded message"""
    try:
        # Find the CONFIG section
        config_start = message_text.find('CONFIG = {')
        if config_start == -1:
            return None
            
        # Find the matching closing brace
        brace_count = 0
        config_end = config_start
        in_config = False
        
        for i, char in enumerate(message_text[config_start:], config_start):
            if char == '{':
                brace_count += 1
                in_config = True
            elif char == '}':
                brace_count -= 1
                if in_config and brace_count == 0:
                    config_end = i + 1
                    break
        
        config_text = message_text[config_start:config_end]
        return config_text
    except Exception as e:
        print(f"Error extracting config: {e}")
        return None

def read_template_file(template_name):
    """Read the template file content"""
    try:
        template_file = TEMPLATES.get(template_name)
        if not template_file:
            print(f"Template '{template_name}' not found in TEMPLATES")
            return None
            
        if not os.path.exists(template_file):
            print(f"Template file does not exist: {template_file}")
            return None
        
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Successfully read template file: {template_file} ({len(content)} chars)")
            return content
    except Exception as e:
        print(f"Error reading template file {template_name}: {e}")
        traceback.print_exc()
        return None

def replace_config_in_template(template_content, new_config):
    """Replace the configuration in template file (lines 19-47)"""
    try:
        lines = template_content.split('\n')
        
        # Remove lines 18-46 (0-indexed, so 18-46 covers lines 19-47)
        if len(lines) >= 47:
            # Keep lines before config
            before_config = lines[:18]
            # Keep lines after config
            after_config = lines[47:]
            
            # Insert new config
            new_lines = before_config + [new_config] + after_config
            return '\n'.join(new_lines)
        else:
            # If template is shorter, just append the config
            return template_content + '\n\n' + new_config
            
    except Exception as e:
        print(f"Error replacing config: {e}")
        traceback.print_exc()
        return None

def create_template_keyboard():
    """Create inline keyboard for template selection"""
    markup = InlineKeyboardMarkup(row_width=1)
    
    # Only add buttons for templates that exist
    available_templates = []
    for template_name, template_file in TEMPLATES.items():
        if os.path.exists(template_file):
            available_templates.append(template_name)
    
    if not available_templates:
        # No templates available, create a message about it
        return None
    
    buttons = []
    for template_name in available_templates:
        if template_name == 'naira':
            buttons.append(InlineKeyboardButton("💰 Naira Bot Template", callback_data="template_naira"))
        elif template_name == 'ton':
            buttons.append(InlineKeyboardButton("🪙 TON Bot Template", callback_data="template_ton"))
        elif template_name == 'star':
            buttons.append(InlineKeyboardButton("⭐ Star Bot Template", callback_data="template_star"))
    
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    # Check which templates are available
    available_templates = []
    for template_name, template_file in TEMPLATES.items():
        if os.path.exists(template_file):
            available_templates.append(template_name.upper())
    
    if available_templates:
        templates_text = f"Available templates: {', '.join(available_templates)}"
    else:
        templates_text = "⚠️ No template files found. Please add template files to use this bot."
    
    bot.reply_to(message, 
        "👋 Welcome to Bot Template Creator!\n\n"
        "To create a new bot:\n"
        "1. Forward me a configuration message\n"
        "2. Select your preferred template\n"
        "3. Get your customized bot file!\n\n"
        f"{templates_text}\n\n"
        "Send me a configuration message to get started.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    
    try:
        # Debug: Print message info
        print(f"Message from user: {user_id}")
        print(f"Message text preview: {message.text[:100] if message.text else 'No text'}...")
        
        # Check if this is a forwarded configuration message
        if message.text and "New Bot Creation Request" in message.text and "CONFIG = {" in message.text:
            # Extract configuration
            config = extract_config_from_message(message.text)
            
            if config:
                user_configs[user_id] = config
                user_states[user_id] = 'waiting_template'
                
                print(f"Config stored for user {user_id}")
                print(f"Config preview: {config[:100]}...")
                
                keyboard = create_template_keyboard()
                if keyboard:
                    bot.reply_to(message, 
                        "✅ Configuration extracted successfully!\n\n"
                        "Please select the bot template you'd like to use:",
                        reply_markup=keyboard)
                else:
                    bot.reply_to(message, 
                        "✅ Configuration extracted successfully!\n\n"
                        "❌ However, no template files are available. "
                        "Please contact the bot administrator to add template files.")
            else:
                bot.reply_to(message, 
                    "❌ Could not extract configuration from the message. "
                    "Please make sure you forwarded a valid configuration message.")
        
        elif user_id in user_states and user_states[user_id] == 'waiting_config':
            # This handles the case where user sends config after selecting template
            if message.text and "CONFIG = {" in message.text:
                config = extract_config_from_message(message.text)
                if config:
                    user_configs[user_id] = config
                    # Process with previously selected template
                    process_bot_creation(message, user_states.get(f"{user_id}_template"))
                else:
                    bot.reply_to(message, "❌ Invalid configuration format. Please forward a valid configuration message.")
            else:
                bot.reply_to(message, "Please forward a valid configuration message containing 'CONFIG = {'")
        
        else:
            # Regular message - ask for configuration
            bot.reply_to(message, 
                "Please forward me a configuration message that contains:\n"
                "- 'New Bot Creation Request'\n"
                "- 'CONFIG = {' section\n\n"
                "Or use /start to see instructions.")
                
    except Exception as e:
        print(f"Error in handle_message: {e}")
        traceback.print_exc()
        bot.reply_to(message, "❌ An unexpected error occurred. Please try again.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('template_'))
def handle_template_selection(call):
    user_id = call.from_user.id
    template_type = call.data.replace('template_', '')
    
    try:
        # Answer the callback query first
        bot.answer_callback_query(call.id)
        
        # Debug: Print user configs to see what's stored
        print(f"User ID: {user_id}")
        print(f"Stored configs: {list(user_configs.keys())}")
        print(f"Config exists for user: {user_id in user_configs}")
        
        # Check if user has config ready
        if user_id in user_configs:
            # User already sent config, process immediately
            bot.edit_message_text(
                f"🔄 Processing {template_type.upper()} template...",
                call.message.chat.id,
                call.message.message_id
            )
            process_bot_creation_from_callback(call, template_type)
        else:
            # Store template choice and ask for config
            user_states[user_id] = 'waiting_config'
            user_states[f"{user_id}_template"] = template_type
            
            bot.edit_message_text(
                f"✅ {template_type.upper()} template selected!\n\n"
                "Now please forward me the configuration message.",
                call.message.chat.id,
                call.message.message_id
            )
    except Exception as e:
        print(f"Error in handle_template_selection: {e}")
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ An error occurred. Please try again.")

def process_bot_creation_from_callback(call, template_type):
    """Process the bot creation with config and template from callback"""
    user_id = call.from_user.id
    
    try:
        # Get the configuration
        config = user_configs.get(user_id)
        if not config:
            bot.edit_message_text(
                "❌ No configuration found. Please forward the configuration message first.",
                call.message.chat.id,
                call.message.message_id
            )
            return
        
        # Read template file
        template_content = read_template_file(template_type)
        if not template_content:
            bot.edit_message_text(
                f"❌ Could not read {template_type} template file. Template file '{TEMPLATES.get(template_type)}' is missing or unreadable.",
                call.message.chat.id,
                call.message.message_id
            )
            return
        
        # Replace config in template
        new_bot_content = replace_config_in_template(template_content, config)
        if not new_bot_content:
            bot.edit_message_text(
                "❌ Could not process the template. Please try again.",
                call.message.chat.id,
                call.message.message_id
            )
            return
        
        # Extract bot name for filename
        bot_name = "custom_bot"
        try:
            if '"BOT_NAME"' in config:
                bot_name_match = re.search(r'"BOT_NAME":\s*"([^"]+)"', config)
                if bot_name_match:
                    bot_name = bot_name_match.group(1).lower().replace(' ', '_')
        except:
            pass
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(new_bot_content)
            tmp_file_path = tmp_file.name
        
        # Update message to show completion
        bot.edit_message_text(
            f"✅ {template_type.upper()} bot created successfully!",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Send file to user
        filename = f"{bot_name}_{template_type}_bot.py"
        
        with open(tmp_file_path, 'rb') as file:
            bot.send_document(
                call.message.chat.id,
                file,
                caption=f"🤖 Your {template_type.upper()} bot is ready!\n\n"
                       f"📁 Filename: {filename}\n"
                       f"✅ Configuration applied successfully!\n\n"
                       f"You can now run this bot file.",
                visible_file_name=filename
            )
        
        # Clean up
        os.unlink(tmp_file_path)
        cleanup_user_data(user_id)
            
        bot.send_message(call.message.chat.id, "✅ Bot created successfully! You can create another bot by forwarding a new configuration message.")
        
    except Exception as e:
        bot.edit_message_text(
            f"❌ An error occurred while creating the bot: {str(e)}",
            call.message.chat.id,
            call.message.message_id
        )
        print(f"Error in process_bot_creation_from_callback: {e}")
        traceback.print_exc()

def process_bot_creation(message, template_type):
    """Process the bot creation with config and template"""
    user_id = message.from_user.id
    
    try:
        # Get the configuration
        config = user_configs.get(user_id)
        if not config:
            bot.send_message(message.chat.id, "❌ No configuration found. Please forward the configuration message first.")
            return
        
        # Send processing message
        processing_msg = bot.send_message(message.chat.id, f"🔄 Creating your {template_type.upper()} bot...")
        
        # Read template file
        template_content = read_template_file(template_type)
        if not template_content:
            bot.edit_message_text(
                f"❌ Could not read {template_type} template file. Template file '{TEMPLATES.get(template_type)}' is missing or unreadable.",
                message.chat.id,
                processing_msg.message_id
            )
            return
        
        # Replace config in template
        new_bot_content = replace_config_in_template(template_content, config)
        if not new_bot_content:
            bot.edit_message_text(
                "❌ Could not process the template. Please try again.",
                message.chat.id,
                processing_msg.message_id
            )
            return
        
        # Extract bot name for filename
        bot_name = "custom_bot"
        try:
            if '"BOT_NAME"' in config:
                bot_name_match = re.search(r'"BOT_NAME":\s*"([^"]+)"', config)
                if bot_name_match:
                    bot_name = bot_name_match.group(1).lower().replace(' ', '_')
        except:
            pass
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(new_bot_content)
            tmp_file_path = tmp_file.name
        
        # Delete processing message
        bot.delete_message(message.chat.id, processing_msg.message_id)
        
        # Send file to user
        filename = f"{bot_name}_{template_type}_bot.py"
        
        with open(tmp_file_path, 'rb') as file:
            bot.send_document(
                message.chat.id,
                file,
                caption=f"🤖 Your {template_type.upper()} bot is ready!\n\n"
                       f"📁 Filename: {filename}\n"
                       f"✅ Configuration applied successfully!\n\n"
                       f"You can now run this bot file.",
                visible_file_name=filename
            )
        
        # Clean up
        os.unlink(tmp_file_path)
        cleanup_user_data(user_id)
            
        bot.send_message(message.chat.id, "✅ Bot created successfully! You can create another bot by forwarding a new configuration message.")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred while creating the bot: {str(e)}")
        print(f"Error in process_bot_creation: {e}")
        traceback.print_exc()

def cleanup_user_data(user_id):
    """Clean up user data from memory"""
    if user_id in user_configs:
        del user_configs[user_id]
    if user_id in user_states:
        del user_states[user_id]
    if f"{user_id}_template" in user_states:
        del user_states[f"{user_id}_template"]

def check_template_files():
    """Check which template files exist and report status"""
    print("\n📋 Template File Status:")
    print("-" * 40)
    
    all_exist = True
    for template_name, template_file in TEMPLATES.items():
        if os.path.exists(template_file):
            file_size = os.path.getsize(template_file)
            print(f"✅ {template_name.upper()}: {template_file} ({file_size} bytes)")
        else:
            print(f"❌ {template_name.upper()}: {template_file} (NOT FOUND)")
            all_exist = False
    
    print("-" * 40)
    
    if not all_exist:
        print("⚠️  WARNING: Some template files are missing!")
        print("   Create the missing files or the bot will have limited functionality.")
    else:
        print("✅ All template files found!")
    
    return all_exist

if __name__ == "__main__":
    print("🤖 Bot Template Creator is starting...")
    
    # Check template files
    check_template_files()
    
    print("\nBot is ready to receive configuration messages!")
    
    try:
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot stopped with error: {e}")
        traceback.print_exc()