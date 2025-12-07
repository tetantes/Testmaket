import json
import telebot
import os
import time
import re
import html
import requests
import logging
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMember

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "" 
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 6341715879
CHANNEL_USERNAME = "tenocobotmaker"
CHANNEL_LINK = "https://t.me/tenocobotmaker"
DATABASE_FILE = "database.json"

if not os.path.exists(DATABASE_FILE):
    logger.info(f"Database file '{DATABASE_FILE}' not found. Creating...")
    try:
        with open(DATABASE_FILE, "w") as f:
            json.dump({"users": {}}, f, indent=4)
        logger.info(f"Database file '{DATABASE_FILE}' created successfully.")
    except Exception as e:
        logger.error(f"Failed to create database file '{DATABASE_FILE}': {e}", exc_info=True)

def load_database():
    try:
        with open(DATABASE_FILE, "r") as f:
            data = json.load(f)
            if "users" not in data:
                logger.warning(f"Database file '{DATABASE_FILE}' is missing 'users' key. Initializing.")
                return {"users": {}}
            return data
    except FileNotFoundError:
        logger.error(f"Database file not found: {DATABASE_FILE}. Returning empty structure.")
        return {"users": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from database file '{DATABASE_FILE}': {e}. Returning empty structure.")
        return {"users": {}}
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading the database '{DATABASE_FILE}': {e}", exc_info=True)
        return {"users": {}}

def save_database(data):
    try:
        with open(DATABASE_FILE, "w") as f:
            json.dump(data, f, indent=4)
        logger.debug(f"Database saved successfully to {DATABASE_FILE}")
    except Exception as e:
        logger.error(f"An error occurred while saving the database '{DATABASE_FILE}': {e}", exc_info=True)

user_states = {}
user_data = {}
BOT_TEMPLATES = ["🌟 STAR BOT"]
broadcast_temp_data = {}

def validate_bot_token(token):
    api_url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get("ok"):
                logger.info(f"Token validation successful for bot: {bot_info['result']['username']}")
                return True, bot_info["result"]
            else:
                logger.warning(f"Token validation failed. API response not OK: {response.text}")
                return False, None
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout during token validation ({api_url}).")
        return False, None
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred during token validation: {http_err} - Response: {response.text}")
        return False, None
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error during token validation: {req_err}")
        return False, None
    except Exception as e:
        logger.error(f"An unexpected error occurred during token validation: {e}", exc_info=True)
        return False, None

def join_channel_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("➡️ Join Channel", url=CHANNEL_LINK))
    markup.row(InlineKeyboardButton("✅ Continue", callback_data="check_subscription"))
    return markup

def main_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🤖 Create bot", callback_data="create_bot"))
    markup.row(InlineKeyboardButton("🔍 My bots", callback_data="my_bots"))
    markup.row(InlineKeyboardButton("👤 My account", callback_data="my_account"))
    return markup

def check_membership(user_id):
    try:
        member = bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        logger.debug(f"Membership check for user {user_id} in @{CHANNEL_USERNAME}: Status={member.status}")
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Could not check membership for user {user_id} in @{CHANNEL_USERNAME}: {e}", exc_info=False)
        if "user not found" in str(e).lower():
             logger.warning(f"User {user_id} not found in chat @{CHANNEL_USERNAME}.")
        elif "bot is not a member" in str(e).lower() or "chat not found" in str(e).lower() or "have no rights to send a message" in str(e).lower():
             logger.error(f"CRITICAL: Bot is likely not an admin in @{CHANNEL_USERNAME} or channel is incorrect/private.")
        return False

def send_welcome_message(chat_id, user_id, username, first_name):
    user_id_str = str(user_id)
    try:
        database = load_database()
        if user_id_str not in database["users"]:
            logger.info(f"New user detected: {first_name} (@{username}, ID: {user_id_str}). Registering.")
            database["users"][user_id_str] = {
                "username": username if username else "Unknown",
                "first_name": first_name if first_name else "Unknown",
                "registration_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "bots": []
            }
            save_database(database)
        else:
            # Update username/first_name if changed
            if database["users"][user_id_str].get("username") != (username if username else "Unknown") or \
               database["users"][user_id_str].get("first_name") != (first_name if first_name else "Unknown"):
                 logger.info(f"Updating user info for {user_id_str}.")
                 database["users"][user_id_str]["username"] = username if username else "Unknown"
                 database["users"][user_id_str]["first_name"] = first_name if first_name else "Unknown"
                 save_database(database)

        welcome_msg = f"✅ Welcome back to BotMaker, @{username if username else first_name}!\n\n"
        welcome_msg += "I can help you create and manage your Telegram bots without coding.\n\n"
        welcome_msg += "Please select an option from the menu below:"
        bot.send_message(chat_id, welcome_msg, reply_markup=main_menu_keyboard(), parse_mode="HTML")
        logger.info(f"Sent welcome message and main menu to user {user_id_str}.")
    except Exception as e:
        logger.error(f"Error during welcome message sending/user registration for {user_id_str}: {e}", exc_info=True)
        try:
            bot.send_message(chat_id, "An error occurred while processing your request.\n\nPlease try again later.")
        except Exception as send_error:
             logger.error(f"Failed even to send error message to chat {chat_id}: {send_error}", exc_info=True)

def get_chat_info_from_link(link):
    match_username = re.match(r"^https?://t\.me/([a-zA-Z0-9_]{5,32})$", link)
    if match_username:
        identifier = f"@{match_username.group(1)}"
        try:
            chat = bot.get_chat(identifier)
            if chat.type == 'private' and hasattr(chat, 'username') and chat.username and chat.username.lower().endswith('bot'):
                 logger.warning(f"Link {link} points to a bot ({identifier}), not suitable as a channel/group for must_join.")
                 return None, None
            return chat.type, identifier
        except Exception as e:
            # Log less verbosely if it's a common "chat not found" for non-existent usernames
            if "chat not found" not in str(e).lower():
                logger.warning(f"Could not get chat info for {identifier} from link {link}: {e}")
            else:
                logger.debug(f"Chat info not found for {identifier} (likely not a public channel/group with this username): {e}")
            return None, None
    return None, None


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    logger.info(f"Received /start command from user {first_name or 'N/A'} (@{username or 'N/A'}, ID: {user_id})")

    if check_membership(user_id):
        logger.info(f"User {user_id} is already a member of @{CHANNEL_USERNAME}. Proceeding to welcome.")
        send_welcome_message(message.chat.id, user_id, username, first_name)
    else:
        logger.info(f"User {user_id} is not a member of @{CHANNEL_USERNAME}. Asking to join.")
        msg = f"👋 Hello {html.escape(first_name or 'User')} (@{html.escape(username or 'User')})!\n\n" \
              f"Please join our main channel <a href=\"{CHANNEL_LINK}\">{CHANNEL_USERNAME}</a> for updates and announcements before continuing using the bot."
        try:
            bot.send_message(message.chat.id, msg, reply_markup=join_channel_keyboard(), parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send join request message to user {user_id}: {e}", exc_info=True)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    user_id_str = str(user_id)
    username = call.from_user.username
    first_name = call.from_user.first_name
    logger.info(f"Received callback '{call.data}' from user {first_name or 'N/A'} (@{username or 'N/A'}, ID: {user_id})")

    if call.data == "check_subscription":
        try:
            bot.answer_callback_query(call.id)
            if check_membership(user_id):
                logger.info(f"User {user_id} passed subscription check via callback. Sending welcome.")
                try:
                    welcome_msg = f"✅ Welcome to BotMaker, @{username if username else first_name}!\n\n"
                    welcome_msg += "Thank you for joining the channel.\n\n"
                    welcome_msg += "I can help you create and manage your Telegram bots without coding.\n\n"
                    welcome_msg += "Please select an option from the menu below:"
                    bot.edit_message_text(welcome_msg, call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard(), parse_mode="HTML")
                    database = load_database()
                    if user_id_str not in database["users"]:
                         logger.info(f"New user detected post-subscription: {first_name or 'N/A'} (@{username or 'N/A'}, ID: {user_id_str}). Registering.")
                         database["users"][user_id_str] = {
                             "username": username if username else "Unknown",
                             "first_name": first_name if first_name else "Unknown",
                             "registration_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                             "bots": []
                         }
                         save_database(database)
                except Exception as edit_err:
                    logger.warning(f"Failed to edit message for user {user_id} after subscription check: {edit_err}. Sending new welcome message.", exc_info=False)
                    send_welcome_message(call.message.chat.id, user_id, username, first_name)
            else:
                logger.info(f"User {user_id} clicked continue but is still not subscribed to @{CHANNEL_USERNAME}.")
                bot.answer_callback_query(call.id, f"⚠️ Please join the channel @{CHANNEL_USERNAME} first!", show_alert=True)
        except Exception as e:
            logger.error(f"Error handling 'check_subscription' callback for user {user_id}: {e}", exc_info=True)
            try:
                bot.answer_callback_query(call.id, "An error occurred. Please try again.", show_alert=True)
            except Exception: pass
        return

    elif call.data == "show_admin_instructions":
        bot.answer_callback_query(call.id)
        instructions = (
            "<b>How to make your new bot an Administrator:</b>\n\n"
            "1. Open the Telegram Channel/Group where the bot needs admin rights.\n"
            "2. Go to Channel/Group Info.\n"
            "3. Tap on 'Administrators' (or 'Edit' then 'Administrators').\n"
            "4. Tap 'Add Admin'.\n"
            "5. Search for your new bot's username (e.g., <code>@YourNewBot_bot</code> that you are creating).\n"
            "6. Select your bot.\n"
            "7. Grant necessary permissions (e.g., 'Post messages' for payment channels; for mandatory join checks, the bot needs to be able to see members, which is usually default for admins).\n"
            "8. Save the changes.\n\n"
            "Once done, you can proceed with the setup here."
        )
        original_markup = call.message.reply_markup
        preserved_markup = None
        if original_markup:
            for row in original_markup.keyboard:
                for button in row:
                    if button.callback_data in ["payment_channel_admin_done", "must_join_admin_done"]:
                        preserved_markup = original_markup
                        break
                if preserved_markup:
                    break
        bot.send_message(call.message.chat.id, instructions, parse_mode="HTML", reply_markup=preserved_markup)
        return

    elif call.data == "confirm_broadcast":
        if str(call.from_user.id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "⛔ Unauthorized!", show_alert=True)
            logger.warning(f"Unauthorized broadcast confirmation by {user_id_str}")
            return
        data = broadcast_temp_data.get(str(ADMIN_ID))
        if not data:
            bot.answer_callback_query(call.id, "Error: No broadcast data found. Please start over with /broadcast.", show_alert=True)
            try:
                bot.edit_message_text("Broadcast data lost or expired. Please use /broadcast again.", call.message.chat.id, call.message.message_id)
            except Exception: pass
            return
        bot.answer_callback_query(call.id, "Commencing broadcast...")
        try:
            bot.edit_message_text("🚀 Initiating broadcast to all users. This may take some time...", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        except Exception: pass
        send_broadcast_messages(ADMIN_ID, data["text"], data["photo_id"], data["video_id"], data["parse_mode"])
        broadcast_temp_data.pop(str(ADMIN_ID), None)
        return

    elif call.data == "cancel_broadcast":
        if str(call.from_user.id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "⛔ Unauthorized!", show_alert=True)
            logger.warning(f"Unauthorized broadcast cancellation by {user_id_str}")
            return
        bot.answer_callback_query(call.id, "Broadcast cancelled.")
        try:
            bot.edit_message_text("✅ Broadcast has been cancelled by Admin.", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        except Exception: pass
        broadcast_temp_data.pop(str(ADMIN_ID), None)
        logger.info(f"Admin {ADMIN_ID} cancelled broadcast.")
        return

    if call.data == "payment_channel_admin_done":
        bot.answer_callback_query(call.id)
        if user_states.get(user_id_str) == "awaiting_payment_channel_admin_confirm":
            logger.info(f"User {user_id_str} confirmed adminship for payment channel. Proceeding.")
            user_states[user_id_str] = "awaiting_must_join_channels"
            msg = "🔗 Payment channel noted.\n\n"
            msg += "Now, let's add <b>Must Join Channels/Links</b>.\n\n"
            msg += "Send me the link (e.g., <code>https://t.me/MyUpdateChannel</code> or <code>https://example.com</code>) for each you want users to join.\n\n"
            msg += "If it's a public Telegram Channel, I'll ask if it's mandatory. For mandatory checks to work, your new bot must be an <b>admin</b> there.\n"
            msg += "For Telegram Groups or any non-Telegram web links, they'll be added directly without a mandatory check or admin prompt.\n\n"
            msg += "When you have added all, type <code>/done</code>."
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="HTML")
        else:
            bot.send_message(call.message.chat.id, "Please follow the current step in the bot creation process.", reply_markup=main_menu_keyboard())
        return

    if call.data == "must_join_admin_done":
        bot.answer_callback_query(call.id)
        current_user_state = user_states.get(user_id_str)
        if current_user_state == "awaiting_must_join_public_channel_admin_confirm" and \
           "pending_channel_for_admin_check" in user_data.get(user_id_str, {}):
            logger.info(f"User {user_id_str} confirmed adminship for a public must-join channel. Proceeding to ask mandatory.")
            user_data[user_id_str]["current_channel"] = user_data[user_id_str].pop("pending_channel_for_admin_check")
            channel_data = user_data[user_id_str]["current_channel"]
            user_states[user_id_str] = "awaiting_must_join_mandatory_choice"
            logger.info(f"User {user_id_str} state changed to 'awaiting_must_join_mandatory_choice' for channel {channel_data['url']}")
            markup = InlineKeyboardMarkup()
            markup.row(
                 InlineKeyboardButton("✅ Yes (Mandatory)", callback_data="must_join_yes"),
                 InlineKeyboardButton("❌ No (Optional)", callback_data="must_join_no")
            )
            bot.edit_message_text(f"Okay, for Public Channel: {html.escape(channel_data['url'])}\n\n"
                                  f"❓ <b>Should joining this be MANDATORY for users?</b>\n"
                                  f"<i>(Remember: This only works effectively if your new bot is an admin there!)</i>",
                                  call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        else:
            logger.warning(f"User {user_id_str} clicked 'must_join_admin_done' in unexpected state: {current_user_state} or missing data.")
            bot.send_message(call.message.chat.id, "There was an issue. Please send the channel link again or type /done.", parse_mode="HTML")
        return

    if call.data in ["must_join_yes", "must_join_no"]:
        bot.answer_callback_query(call.id)
        current_user_state = user_states.get(user_id_str)
        if current_user_state == "awaiting_must_join_mandatory_choice" and \
           user_id_str in user_data and "current_channel" in user_data[user_id_str]:
            channel_data = user_data[user_id_str]["current_channel"]
            is_mandatory_option_relevant = channel_data.get("is_public_channel", False) # Should be True here
            channel_data["check"] = (call.data == "must_join_yes") if is_mandatory_option_relevant else False
            channel_data["name"] = f"Channel {len(user_data[user_id_str].get('must_join_channels', [])) + 1}"
            if "must_join_channels" not in user_data[user_id_str]:
                user_data[user_id_str]["must_join_channels"] = []
            user_data[user_id_str]["must_join_channels"].append(channel_data)
            user_data[user_id_str].pop("current_channel", None)
            user_states[user_id_str] = "awaiting_must_join_channels" # CRITICAL FIX
            logger.info(f"User {user_id_str} state set to 'awaiting_must_join_channels' after mandatory choice for {channel_data['url']}.")
            mandatory_text = f"\nIt will{' ' if channel_data['check'] else ' <b>NOT</b> '}be a MANDATORY join." if is_mandatory_option_relevant else ""
            bot.edit_message_text(
                f"Link added: {html.escape(channel_data['url'])}{mandatory_text}\n\nPlease send another channel/group/web link, or type <code>/done</code> to continue.",
                call.message.chat.id, call.message.message_id, parse_mode="HTML"
            )
            logger.info(f"User {user_id_str} processed must-join: {channel_data['url']} (Mandatory: {channel_data['check'] if is_mandatory_option_relevant else 'N/A'})")
        else:
            logger.warning(f"Received '{call.data}' callback from user {user_id_str} in unexpected state: {current_user_state} or 'current_channel' data missing.")
            bot.answer_callback_query(call.id, "Session expired or invalid action. Please send the link again.", show_alert=True)
        return

    # General callback processing starts after specific handlers
    try:
        if call.data == "create_bot":
            bot.answer_callback_query(call.id)
            database = load_database()
            if user_id_str in database["users"] and len(database["users"][user_id_str].get("bots", [])) >= 10:
                bot.send_message(call.message.chat.id, "⚠️ You have reached the maximum limit of <b>10 bots!</b>", parse_mode="HTML")
                logger.info(f"User {user_id_str} tried to create bot but reached limit.")
                return
            markup = InlineKeyboardMarkup()
            for template in BOT_TEMPLATES:
                 safe_template_name = template.replace(":", "_")
                 markup.row(InlineKeyboardButton(template, callback_data=f"template:{safe_template_name}"))
            markup.row(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"))
            bot.edit_message_text("Please select a bot template to start:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
            logger.info(f"User {user_id_str} initiated bot creation. Showing templates.")

        elif call.data.startswith("template:"):
            bot.answer_callback_query(call.id)
            template_name = call.data.split(":", 1)[1]
            original_template_name = template_name.replace("_", ":")
            if original_template_name in BOT_TEMPLATES:
                 logger.info(f"User {user_id_str} selected template: {original_template_name}")
                 user_data[user_id_str] = {
                     "template": original_template_name,
                     "must_join_channels": []
                 }
                 user_states[user_id_str] = "awaiting_bot_token"
                 msg = "Great! Let's start configuring your bot.\n\n"
                 msg += "Please send me the <b>API token</b> for the bot you want to create.\n\n"
                 msg += "To get a token:\n"
                 msg += "1. Open a chat with @BotFather on Telegram.\n"
                 msg += "2. Send the <code>/newbot</code> command.\n"
                 msg += "3. Follow the instructions to choose a name and username.\n"
                 msg += "4. @BotFather will provide the API token. <b>Copy the token and paste it here.</b>"
                 markup = InlineKeyboardMarkup()
                 markup.row(InlineKeyboardButton("🔙 Cancel Creation", callback_data="back_to_main"))
                 bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
            else:
                 logger.warning(f"User {user_id_str} selected an unknown template: {template_name}")
                 bot.edit_message_text("Invalid template selected. Please try again.", call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard())

        elif call.data == "my_bots":
            bot.answer_callback_query(call.id)
            database = load_database()
            user_bots_list = database.get("users", {}).get(user_id_str, {}).get("bots", [])
            logger.debug(f"My Bots for {user_id_str}: {user_bots_list}") # Log the raw list
            if not user_bots_list:
                markup = InlineKeyboardMarkup()
                markup.row(InlineKeyboardButton("🤖 Create a bot", callback_data="create_bot"))
                markup.row(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"))
                bot.edit_message_text("You haven't created any bots with me yet.\n\nWould you like to create one now?", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
                logger.info(f"User {user_id_str} viewed 'My Bots' but has none.")
            else:
                 markup = InlineKeyboardMarkup(row_width=1)
                 for bot_entry in user_bots_list:
                     bot_name = bot_entry.get('bot_name', 'Unnamed Bot')
                     bot_username_cb = bot_entry.get('bot_username', 'Unknown Username') # Should be like @username_bot
                     bot_status = bot_entry.get('status', 'Unknown')
                     # Pass bot_username_cb directly as it includes '@' which is consistent with storage
                     markup.add(InlineKeyboardButton(f"{bot_name} (@{bot_username_cb.lstrip('@')}) - {bot_status}", callback_data=f"bot_info:{bot_username_cb}"))
                 markup.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"))
                 bot.edit_message_text(f"Here are the bots you've created (Total: {len(user_bots_list)}):", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
                 logger.info(f"User {user_id_str} viewed 'My Bots'. Displayed {len(user_bots_list)} bots.")

        elif call.data.startswith("bot_info:"):
            bot.answer_callback_query(call.id)
            bot_username_to_find = call.data.split(":", 1)[1] # This will be like "@username_bot"
            logger.info(f"User {user_id_str} trying to view bot info for: '{bot_username_to_find}'")
            database = load_database()
            user_bots_list = database.get("users", {}).get(user_id_str, {}).get("bots", [])
            
            # Detailed logging for Issue 1 Diagnosis
            db_bot_usernames = [b.get('bot_username') for b in user_bots_list]
            logger.debug(f"User {user_id_str} looking for '{bot_username_to_find}'. Bots in DB for user: {db_bot_usernames}")

            bot_data_entry = None
            for b_entry in user_bots_list:
                 current_bot_username_in_db = b_entry.get("bot_username")
                 logger.debug(f"Comparing query:'{bot_username_to_find}' with DB entry:'{current_bot_username_in_db}'")
                 if current_bot_username_in_db == bot_username_to_find:
                     bot_data_entry = b_entry
                     logger.info(f"Found match for '{bot_username_to_find}'")
                     break
            
            if bot_data_entry:
                msg = f"🤖 <b>Bot Details</b>\n\n"
                msg += f"<b>Name:</b> {html.escape(bot_data_entry.get('bot_name', 'N/A'))}\n"
                msg += f"<b>Username:</b> {html.escape(bot_data_entry.get('bot_username', 'N/A'))}\n" # Show with @
                msg += f"<b>Status:</b> {html.escape(bot_data_entry.get('status', 'Unknown'))}\n"
                msg += f"<b>Requested:</b> {html.escape(bot_data_entry.get('creation_request_date', 'N/A'))}\n"
                config_details_str = bot_data_entry.get('config_details', 'Configuration not available.')
                max_config_len = 3000
                truncated_config = config_details_str[:max_config_len] + ("..." if len(config_details_str) > max_config_len else "")
                msg += f"\n<b>Configuration:</b>\n<pre><code class=\"language-python\">{html.escape(truncated_config)}</code></pre>\n"
                markup = InlineKeyboardMarkup()
                markup.row(InlineKeyboardButton("🛠️ Edit Bot (Recreates)", callback_data=f"edit_bot_warn:{bot_username_to_find}"))
                markup.row(InlineKeyboardButton("🗑️ Delete Bot", callback_data=f"delete_bot:{bot_username_to_find}"))
                markup.row(InlineKeyboardButton("🔙 Back to My Bots", callback_data="my_bots"))
                bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
                logger.info(f"User {user_id_str} viewed info for bot {bot_username_to_find}.")
            else:
                 logger.warning(f"User {user_id_str} tried to view info for bot {bot_username_to_find}, but it was NOT found in their list: {db_bot_usernames}")
                 bot.edit_message_text("Error: Could not find details for this bot.\n\nIt might have been deleted or there was an issue retrieving its data.", call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard(), parse_mode="HTML")

        elif call.data.startswith("edit_bot_warn:"):
            bot.answer_callback_query(call.id)
            bot_username_to_edit = call.data.split(":", 1)[1] # Includes @
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("⚠️ Yes, Delete & Recreate", callback_data=f"confirm_edit_recreate:{bot_username_to_edit}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"bot_info:{bot_username_to_edit}")
            )
            warn_msg = (f"<b>WARNING!</b> Editing bot <b>{html.escape(bot_username_to_edit)}</b> means its current settings and record will be <b>deleted</b> from My Bots.\n\n"
                        f"You will then be guided to create it again from scratch (you'll need its API token, etc.). This action cannot be undone.\n\n"
                        f"Are you sure you want to proceed?")
            bot.edit_message_text(warn_msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

        elif call.data.startswith("confirm_edit_recreate:"):
            bot_username_to_delete_and_edit = call.data.split(":", 1)[1] # Includes @
            logger.info(f"User {user_id_str} confirmed edit (delete & recreate) for bot {bot_username_to_delete_and_edit}.")
            database = load_database()
            deleted_for_edit = False
            if user_id_str in database.get("users", {}):
                user_bots = database["users"][user_id_str].get("bots", [])
                initial_bot_count = len(user_bots)
                database["users"][user_id_str]["bots"] = [
                    b for b in user_bots if b.get("bot_username") != bot_username_to_delete_and_edit
                ]
                if len(database["users"][user_id_str]["bots"]) < initial_bot_count:
                    deleted_for_edit = True
                    save_database(database)
                    logger.info(f"Bot {bot_username_to_delete_and_edit} deleted for edit by user {user_id_str}.")
            if deleted_for_edit:
                bot.answer_callback_query(call.id, "Bot deleted. Starting recreation...")
                create_markup = InlineKeyboardMarkup()
                for template in BOT_TEMPLATES:
                    safe_template_name = template.replace(":", "_")
                    create_markup.row(InlineKeyboardButton(template, callback_data=f"template:{safe_template_name}"))
                create_markup.row(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"))
                edit_msg = (f"Bot {html.escape(bot_username_to_delete_and_edit)} has been removed.\n\n"
                            "Let's set up the new configuration. Please select a bot template to start:")
                bot.edit_message_text(edit_msg, call.message.chat.id, call.message.message_id, reply_markup=create_markup, parse_mode="HTML")
            else:
                bot.answer_callback_query(call.id, "Error: Could not remove the bot for editing. It might have already been deleted.", show_alert=True)
                logger.warning(f"Failed to find bot {bot_username_to_delete_and_edit} for deletion during edit process by user {user_id_str}.")
                bot.edit_message_text("Could not find the bot to edit. Please check 'My Bots' again.", call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard(), parse_mode="HTML")

        elif call.data.startswith("delete_bot:"):
             bot.answer_callback_query(call.id)
             bot_username_to_delete = call.data.split(":", 1)[1] # Includes @
             logger.warning(f"User {user_id_str} initiated deletion for bot {bot_username_to_delete}.")
             markup = InlineKeyboardMarkup()
             markup.row(
                 InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete:{bot_username_to_delete}"),
                 InlineKeyboardButton("❌ No, Cancel", callback_data=f"bot_info:{bot_username_to_delete}")
              )
             bot.edit_message_text(f"⚠️ <b>Are you sure you want to delete the bot {html.escape(bot_username_to_delete)}?</b>\n\nThis action cannot be undone and will remove its record from 'My Bots'.",
                                   call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

        elif call.data.startswith("confirm_delete:"):
             bot_username_to_delete = call.data.split(":", 1)[1] # Includes @
             logger.info(f"User {user_id_str} confirmed deletion for bot {bot_username_to_delete}.")
             database = load_database()
             deleted = False
             if user_id_str in database.get("users", {}):
                 initial_bot_count = len(database["users"][user_id_str].get("bots", []))
                 database["users"][user_id_str]["bots"] = [
                     b for b in database["users"][user_id_str].get("bots", [])
                     if b.get("bot_username") != bot_username_to_delete
                 ]
                 if len(database["users"][user_id_str]["bots"]) < initial_bot_count:
                      deleted = True
                      save_database(database)
                      logger.info(f"Successfully deleted bot {bot_username_to_delete} for user {user_id_str}.")
             markup = InlineKeyboardMarkup()
             markup.row(InlineKeyboardButton("🔙 Back to My Bots", callback_data="my_bots"))
             if deleted:
                 bot.edit_message_text(f"🗑️ Bot {html.escape(bot_username_to_delete)} has been successfully deleted.", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
             else:
                 logger.error(f"Failed to delete bot {bot_username_to_delete} for user {user_id_str} (maybe already deleted?).")
                 bot.edit_message_text(f"❌ Could not delete bot {html.escape(bot_username_to_delete)}.\n\nIt might have already been removed.", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

        elif call.data == "my_account":
            bot.answer_callback_query(call.id)
            database = load_database()
            user_info = database.get("users", {}).get(user_id_str, {})
            msg = "👤 <b>Account Information</b>\n\n"
            msg += f"<b>User ID:</b> <code>{user_id_str}</code>\n"
            display_username = user_info.get('username', 'Not Set')
            if display_username and display_username != "Unknown":
                 msg += f"<b>Username:</b> @{html.escape(display_username)}\n"
            else:
                 msg += f"<b>Username:</b> Not Set\n"
            msg += f"<b>Registration Date:</b> {user_info.get('registration_date', 'Unknown')}\n"
            msg += f"<b>Bots Created:</b> {len(user_info.get('bots', []))} / 10\n\n"
            msg += "For support, contact @tenocobot\n" # Placeholder
            msg += f"Updates Channel: <a href=\"{CHANNEL_LINK}\">{CHANNEL_USERNAME}</a>"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"))
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
            logger.info(f"User {user_id_str} viewed 'My Account'.")

        elif call.data == "back_to_main":
            bot.answer_callback_query(call.id)
            if user_id_str in user_states:
                 logger.info(f"User {user_id_str} returned to main menu, clearing state '{user_states[user_id_str]}'.")
                 user_states.pop(user_id_str, None)
            if user_id_str in user_data:
                 logger.info(f"User {user_id_str} returned to main menu, clearing user_data.")
                 user_data.pop(user_id_str, None)
            welcome_msg = f"🤖 Welcome back to BotMaker, @{username if username else first_name}!\n\n"
            welcome_msg += "Please select an option from the menu below:"
            bot.edit_message_text(welcome_msg, call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard(), parse_mode="HTML")
            logger.info(f"User {user_id_str} returned to main menu via button.")

        # Admin approval/rejection (ensure bot_username in callbacks includes '@')
        elif call.data.startswith("approve_bot:"):
             if str(call.from_user.id) != str(ADMIN_ID):
                 bot.answer_callback_query(call.id, "⛔ You are not authorized for this action!", show_alert=True)
                 return
             bot.answer_callback_query(call.id, "Processing approval...")
             try:
                 parts = call.data.split(":")
                 requester_id_str, bot_username_app = parts[1], parts[2] # bot_username_app includes @
                 logger.info(f"Admin {ADMIN_ID} initiated approval for bot {bot_username_app} by user {requester_id_str}.")
                 database = load_database()
                 bot_found_updated = False
                 if requester_id_str in database.get("users", {}):
                     for bot_info_entry in database["users"][requester_id_str].get("bots", []):
                         if bot_info_entry.get("bot_username") == bot_username_app:
                             bot_info_entry["status"] = "Approved"
                             save_database(database)
                             bot_found_updated = True
                             logger.info(f"Bot {bot_username_app} status to 'Approved' for user {requester_id_str}.")
                             try:
                                 bot.send_message(int(requester_id_str),
                                                  f"🎉 Good news!\n\nYour bot creation request for <b>{html.escape(bot_username_app)}</b> has been <b>approved</b>.\n\n"
                                                  f"It is now being processed and should be ready within 1-12 hours. I will notify you when it's active.",
                                                  parse_mode="HTML")
                             except Exception as e:
                                 logger.error(f"Failed to notify user {requester_id_str} about bot approval: {e}", exc_info=True)
                                 bot.send_message(ADMIN_ID, f"⚠️ Failed to notify user {requester_id_str} about approval of {html.escape(bot_username_app)}.\nError: {e}")
                             markup_admin = InlineKeyboardMarkup()
                             markup_admin.row(InlineKeyboardButton("✅ Mark as Active", callback_data=f"bot_done:{requester_id_str}:{bot_username_app}"))
                             markup_admin.row(InlineKeyboardButton("❌ Cancel Approval", callback_data=f"bot_cancel:{requester_id_str}:{bot_username_app}"))
                             bot.edit_message_text(f"✅ Bot <b>{html.escape(bot_username_app)}</b> (User: {requester_id_str}) <b>approved</b>.\nUser notified. Use buttons when deployed or to cancel.",
                                                   call.message.chat.id, call.message.message_id, reply_markup=markup_admin, parse_mode="HTML")
                             break
                 if not bot_found_updated:
                     logger.error(f"Admin approval error: Bot {bot_username_app} for user {requester_id_str} not found.")
                     bot.edit_message_text(f"❌ Error: Could not find bot request for {html.escape(bot_username_app)} from user {requester_id_str}.",
                                           call.message.chat.id, call.message.message_id, parse_mode="HTML")
             except Exception as e:
                  logger.error(f"Error during bot approval for {call.data}: {e}", exc_info=True)
                  bot.edit_message_text("Unexpected error during approval.", call.message.chat.id, call.message.message_id)

        elif call.data.startswith("decline_bot:"):
            if str(call.from_user.id) != str(ADMIN_ID):
                bot.answer_callback_query(call.id, "⛔ You are not authorized!", show_alert=True)
                return
            bot.answer_callback_query(call.id, "Processing decline...")
            try:
                parts = call.data.split(":")
                requester_id_str, bot_username_dec = parts[1], parts[2] # Includes @
                logger.info(f"Admin {ADMIN_ID} initiated decline for bot {bot_username_dec} by {requester_id_str}.")
                database = load_database()
                bot_found_removed = False
                if requester_id_str in database.get("users", {}):
                    user_bots_list = database["users"][requester_id_str].get("bots", [])
                    new_bots_list = [b for b in user_bots_list if b.get("bot_username") != bot_username_dec]
                    if len(new_bots_list) < len(user_bots_list):
                        database["users"][requester_id_str]["bots"] = new_bots_list
                        save_database(database)
                        bot_found_removed = True
                        logger.info(f"Bot {bot_username_dec} declined and removed for user {requester_id_str}.")
                        try:
                            bot.send_message(int(requester_id_str),
                                             f"❌ Regarding your bot request for <b>{html.escape(bot_username_dec)}</b>:\n\n"
                                             f"Unfortunately, your request has been <b>declined</b>.\n\n"
                                             f"Please review your setup info or contact support. You can try creating a bot again later.",
                                             parse_mode="HTML")
                        except Exception as e:
                            logger.error(f"Failed to notify user {requester_id_str} of decline: {e}", exc_info=True)
                            bot.send_message(ADMIN_ID, f"⚠️ Failed to notify user {requester_id_str} of decline of {html.escape(bot_username_dec)}.\nError: {e}")
                        bot.edit_message_text(f"❌ Bot request for <b>{html.escape(bot_username_dec)}</b> (User: {requester_id_str}) <b>declined</b> and removed.\nUser notified.",
                                              call.message.chat.id, call.message.message_id, parse_mode="HTML")
                if not bot_found_removed:
                    logger.warning(f"Admin decline error: Bot {bot_username_dec} for user {requester_id_str} not found.")
                    bot.edit_message_text(f"⚠️ Could not find bot request for {html.escape(bot_username_dec)} (User {requester_id_str}) to decline.",
                                          call.message.chat.id, call.message.message_id, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Error during bot decline for {call.data}: {e}", exc_info=True)
                bot.edit_message_text("Unexpected error during decline.", call.message.chat.id, call.message.message_id)

        elif call.data.startswith("bot_done:"):
            if str(call.from_user.id) != str(ADMIN_ID):
                bot.answer_callback_query(call.id, "⛔ Unauthorized!", show_alert=True)
                return
            bot.answer_callback_query(call.id, "Marking as active...")
            try:
                parts = call.data.split(":")
                requester_id_str, bot_username_done = parts[1], parts[2] # Includes @
                logger.info(f"Admin {ADMIN_ID} marking bot {bot_username_done} (User: {requester_id_str}) as 'Active'.")
                database = load_database()
                bot_found_act = False
                if requester_id_str in database.get("users", {}):
                     for bot_info_entry in database["users"][requester_id_str].get("bots", []):
                         if bot_info_entry.get("bot_username") == bot_username_done:
                             bot_info_entry["status"] = "Active"
                             save_database(database)
                             bot_found_act = True
                             logger.info(f"Bot {bot_username_done} status to 'Active' for user {requester_id_str}.")
                             try:
                                  bot.send_message(int(requester_id_str),
                                                  f"🚀 Great news!\n\nYour bot <b>{html.escape(bot_username_done)}</b> is now <b>Active</b> and ready to use!\n\nYou can start interacting with it.",
                                                  parse_mode="HTML")
                             except Exception as e:
                                 logger.error(f"Failed to notify user {requester_id_str} of bot readiness: {e}", exc_info=True)
                                 bot.send_message(ADMIN_ID, f"⚠️ Failed to notify user {requester_id_str} that bot {html.escape(bot_username_done)} is ready.\nError: {e}")
                             bot.edit_message_text(f"✅ Bot <b>{html.escape(bot_username_done)}</b> (User: {requester_id_str}) marked <b>Active</b>.\nUser notified.",
                                                  call.message.chat.id, call.message.message_id, parse_mode="HTML")
                             break
                if not bot_found_act:
                     logger.error(f"Admin mark active error: Bot {bot_username_done} for user {requester_id_str} not found.")
                     bot.edit_message_text(f"❌ Error: Could not find bot {html.escape(bot_username_done)} for user {requester_id_str} to mark active.",
                                           call.message.chat.id, call.message.message_id, parse_mode="HTML")
            except Exception as e:
                  logger.error(f"Error during 'bot_done' for {call.data}: {e}", exc_info=True)
                  bot.edit_message_text("Unexpected error marking bot active.", call.message.chat.id, call.message.message_id)

        elif call.data.startswith("bot_cancel:"):
            if str(call.from_user.id) != str(ADMIN_ID):
                bot.answer_callback_query(call.id, "⛔ Unauthorized!", show_alert=True)
                return
            bot.answer_callback_query(call.id, "Cancelling approval/development...")
            try:
                parts = call.data.split(":")
                requester_id_str, bot_username_can = parts[1], parts[2] # Includes @
                logger.warning(f"Admin {ADMIN_ID} cancelling for bot {bot_username_can} by {requester_id_str}.")
                database = load_database()
                bot_found_can = False
                if requester_id_str in database.get("users", {}):
                    user_bots_list = database["users"][requester_id_str].get("bots", [])
                    new_bots_list = [b for b in user_bots_list if b.get("bot_username") != bot_username_can]
                    if len(new_bots_list) < len(user_bots_list):
                        database["users"][requester_id_str]["bots"] = new_bots_list
                        save_database(database)
                        bot_found_can = True
                        logger.info(f"Bot {bot_username_can} cancelled and removed for user {requester_id_str}.")
                        try:
                            bot.send_message(int(requester_id_str),
                                             f"⚠️ Regarding your bot <b>{html.escape(bot_username_can)}</b>:\n\n"
                                             f"The approval/development has been <b>cancelled</b> by administration.\n\n"
                                             f"Contact support if needed. You may try creating it again later.",
                                             parse_mode="HTML")
                        except Exception as e:
                            logger.error(f"Failed to notify user {requester_id_str} of cancellation: {e}", exc_info=True)
                            bot.send_message(ADMIN_ID, f"⚠️ Failed to notify user {requester_id_str} of cancellation of {html.escape(bot_username_can)}.\nError: {e}")
                        bot.edit_message_text(f"❌ Approval/Development for <b>{html.escape(bot_username_can)}</b> (User: {requester_id_str}) <b>cancelled</b> and removed.\nUser notified.",
                                              call.message.chat.id, call.message.message_id, parse_mode="HTML")
                if not bot_found_can:
                    logger.warning(f"Admin cancel error: Bot {bot_username_can} for user {requester_id_str} not found.")
                    bot.edit_message_text(f"⚠️ Could not find bot {html.escape(bot_username_can)} (User {requester_id_str}) to cancel.",
                                          call.message.chat.id, call.message.message_id, parse_mode="HTML")
            except Exception as e:
                  logger.error(f"Error 'bot_cancel' for {call.data}: {e}", exc_info=True)
                  bot.edit_message_text("Unexpected error during cancellation.", call.message.chat.id, call.message.message_id)
        else:
            # Fallback for unhandled callbacks if no specific handler matched earlier
            # List known prefixes that are handled by specific `startswith` blocks
            known_prefixes = ["template:", "bot_info:", "edit_bot_warn:", "confirm_edit_recreate:", 
                              "delete_bot:", "confirm_delete:", "approve_bot:", "decline_bot:", 
                              "bot_done:", "bot_cancel:"]
            is_known_prefix_callback = any(call.data.startswith(prefix) for prefix in known_prefixes)
            
            # List exact matches that are handled
            known_exact_matches = ["check_subscription", "show_admin_instructions", "confirm_broadcast", 
                                   "cancel_broadcast", "payment_channel_admin_done", "must_join_admin_done",
                                   "must_join_yes", "must_join_no", "create_bot", "my_bots", "my_account", "back_to_main"]

            if not is_known_prefix_callback and call.data not in known_exact_matches:
                 logger.warning(f"Unhandled callback in general try-except: '{call.data}' from user {user_id_str}")
                 try: bot.answer_callback_query(call.id, "Action not recognized or is currently unavailable.")
                 except Exception: pass
    except Exception as e:
        logger.error(f"Generic callback error for callback '{call.data}', user {user_id}: {e}", exc_info=True)
        try: bot.answer_callback_query(call.id, "An internal error occurred. Please try again.", show_alert=True)
        except Exception: pass


@bot.message_handler(func=lambda message: str(message.from_user.id) in user_states and message.content_type == 'text')
def handle_bot_creation(message):
    try:
        user_id_str = str(message.from_user.id)
        state = user_states.get(user_id_str)
        logger.info(f"Msg from user {user_id_str} in state '{state}'. Text: '{message.text[:50]}...'")

        if state and state.startswith("awaiting_must_join") and message.text.strip().lower() == "/done":
            user_data.get(user_id_str, {}).pop("current_channel", None)
            user_data.get(user_id_str, {}).pop("pending_channel_for_admin_check", None)
            user_states[user_id_str] = "awaiting_min_withdrawal"
            bot.send_message(message.chat.id, "👍 Channels/Links stage complete.\n\nNow, what should be the <b>minimum withdrawal amount</b> (e.g., <code>100</code>)?", parse_mode="HTML")
            logger.info(f"User {user_id_str} finished must-join via /done from state {state}. Proceeding to min withdrawal.")
            return

        if state == "awaiting_bot_token":
            token = message.text.strip()
            if ':' not in token or len(token) < 30:
                 bot.send_message(message.chat.id, "⚠️ This doesn't look like a valid bot token.\nPlease get the token from @BotFather and paste it here.", parse_mode="HTML")
                 return
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception as e:
                 logger.warning(f"Could not delete token msg for user {user_id_str}: {e}")
            bot.send_chat_action(message.chat.id, 'typing')
            is_valid, bot_info_data = validate_bot_token(token)
            if is_valid and bot_info_data:
                bot_api_username = bot_info_data.get('username')
                if not bot_api_username:
                    bot.send_message(message.chat.id, "❌ Token is valid, but could not retrieve bot username. This is unusual. Please try another token or contact support.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel Creation", callback_data="back_to_main")), parse_mode="HTML")
                    return
                user_data[user_id_str]["bot_token"] = token
                user_data[user_id_str]["bot_username"] = f"@{bot_api_username}" # Store with @
                user_states[user_id_str] = "awaiting_bot_name"
                bot.send_message(message.chat.id, f"✅ Bot token is valid for <b>@{bot_api_username}</b>!\n(Username automatically detected).\n\nNow, please enter the <b>display name</b> for your bot (e.g., 'My Awesome Bot'):", parse_mode="HTML")
                logger.info(f"User {user_id_str} provided valid token for @{bot_api_username}.")
            else:
                 bot.send_message(message.chat.id, "❌ <b>Invalid bot token.</b>\n\nPlease double-check from @BotFather or click Cancel.",
                                  reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel Creation", callback_data="back_to_main")), parse_mode="HTML")
                 logger.warning(f"User {user_id_str} provided invalid token.")

        elif state == "awaiting_bot_name":
            bot_name = message.text.strip()
            if not bot_name:
                bot.send_message(message.chat.id, "⚠️ Bot name cannot be empty. Please enter a name.")
                return
            if len(bot_name) > 64:
                 bot.send_message(message.chat.id, "⚠️ Bot name too long (max 64 chars). Shorter name please.")
                 return
            user_data[user_id_str]["bot_name"] = bot_name
            user_states[user_id_str] = "awaiting_payment_channel"
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❓ How to make bot admin?", callback_data="show_admin_instructions"))
            bot.send_message(message.chat.id, f"👍 Bot name: <b>{html.escape(bot_name)}</b>\nBot Username: <b>{html.escape(user_data[user_id_str]['bot_username'])}</b>\n\nPlease enter the link to your <b>Payment Proof Channel</b> (must be a public Telegram Channel, e.g., <code>https://t.me/MyPaymentProofs</code>).\n\n<i>Your new bot (<b>{html.escape(user_data[user_id_str]['bot_username'])}</b>) <b>must</b> be an <b>administrator</b> in this channel for it to work.</i>", reply_markup=markup, parse_mode="HTML")
            logger.info(f"User {user_id_str} set bot name to '{bot_name}'. Proceeding to payment channel.")

        elif state == "awaiting_payment_channel":
            channel_link = message.text.strip()
            match = re.match(r"^(https?://)?t\.me/([a-zA-Z0-9_]{5,32})$", channel_link)
            if not match:
                bot.send_message(message.chat.id, "⚠️ Invalid link format or not a public Telegram Channel link.\n\nPlease provide a direct link like <code>https://t.me/YourChannelName</code> (not a group invite link like t.me/joinchat/... or t.me/+...).", parse_mode="HTML")
                return
            user_data[user_id_str]["payment_channel"] = channel_link
            user_states[user_id_str] = "awaiting_payment_channel_admin_confirm"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("✅ Done, Bot is Admin", callback_data="payment_channel_admin_done"))
            markup.add(InlineKeyboardButton("❓ How to make bot admin?", callback_data="show_admin_instructions"))
            bot.send_message(message.chat.id,
                             f"🔗 Payment channel set to: {html.escape(channel_link)}\n\n"
                             f"❗ <b>Crucial:</b> Please ensure your new bot (<b>{html.escape(user_data[user_id_str]['bot_username'])}</b>) is an <b>administrator</b> in this payment channel (<code>{html.escape(channel_link)}</code>) with rights to post messages.\n\n"
                             f"Click 'Done, Bot is Admin' after you've set this up.",
                             reply_markup=markup, parse_mode="HTML")
            logger.info(f"User {user_id_str} set payment channel to '{channel_link}'. Awaiting admin confirmation.")

        elif state == "awaiting_must_join_channels":
            channel_link_input = message.text.strip()

            if "current_channel" in user_data.get(user_id_str, {}) or \
               "pending_channel_for_admin_check" in user_data.get(user_id_str, {}):
                 bot.send_message(message.chat.id, "⚠️ Please complete the admin/mandatory choice for the previous channel/link first before adding another, or type <code>/done</code>.", parse_mode="HTML")
                 return

            # Allow any http/https or t.me link
            if ' ' in channel_link_input or not (channel_link_input.lower().startswith('http://') or channel_link_input.lower().startswith('https://') or channel_link_input.lower().startswith('t.me/')):
                 bot.send_message(message.chat.id, "⚠️ Invalid link format.\n\nPlease send a valid web link (starting with http:// or https://) or a Telegram link (e.g., t.me/channelname).", parse_mode="HTML")
                 return

            is_telegram_link = channel_link_input.lower().startswith('https://t.me/') or channel_link_input.lower().startswith('t.me/')
            is_public_telegram_channel = False
            identified_chat_name_mj = None

            if is_telegram_link:
                # Normalize t.me/ links to https://t.me/ for consistency if needed, though not strictly required here.
                # if not channel_link_input.lower().startswith('https://t.me/'):
                #    channel_link_input = "https://t.me/" + channel_link_input.split("t.me/",1)[1]

                chat_type, identified_chat_name_mj = get_chat_info_from_link(channel_link_input)
                if chat_type == 'channel': # Only 'channel' type implies a public channel suitable for admin/mandatory check
                    is_public_telegram_channel = True
            
            temp_channel_data = {
                "url": channel_link_input,
                "is_public_channel": is_public_telegram_channel, # True only if it's a public Telegram channel
                "identified_name": identified_chat_name_mj 
            }

            if is_public_telegram_channel:
                user_data[user_id_str]["pending_channel_for_admin_check"] = temp_channel_data
                user_states[user_id_str] = "awaiting_must_join_public_channel_admin_confirm"
                markup_mj_admin = InlineKeyboardMarkup()
                markup_mj_admin.add(InlineKeyboardButton("✅ Done, Bot is Admin", callback_data="must_join_admin_done"))
                markup_mj_admin.add(InlineKeyboardButton("❓ How to make bot admin?", callback_data="show_admin_instructions"))
                bot.send_message(message.chat.id,
                                 f"Identified as Public Telegram Channel: {html.escape(channel_link_input)}\n\n"
                                 f"For the 'mandatory join' option to work effectively, your new bot (<b>{html.escape(user_data[user_id_str]['bot_username'])}</b>) needs to be an <b>administrator</b> in <code>{html.escape(identified_chat_name_mj or channel_link_input)}</code>.\n\n"
                                 f"Click 'Done, Bot is Admin' after setting this up (if you plan to make it mandatory).",
                                 reply_markup=markup_mj_admin, parse_mode="HTML")
                logger.info(f"User {user_id_str} submitted Public Telegram Channel for must-join: '{channel_link_input}'. State: {user_states.get(user_id_str)}")
            else: # For non-Telegram links OR non-public-channel Telegram links (groups, private, etc.)
                temp_channel_data["check"] = False # Never mandatory by bot for these types
                temp_channel_data["name"] = f"Link {len(user_data[user_id_str].get('must_join_channels', [])) + 1}"
                if "must_join_channels" not in user_data[user_id_str]:
                    user_data[user_id_str]["must_join_channels"] = []
                user_data[user_id_str]["must_join_channels"].append(temp_channel_data)
                link_type_msg = "Telegram link (group/private)" if is_telegram_link else "External web link"
                bot.send_message(message.chat.id,
                                 f"{link_type_msg} added: {html.escape(channel_link_input)}\n(This type of link will not have a mandatory join check performed by the bot).\n\n"
                                 f"Send another link, or type <code>/done</code> to continue.",
                                 parse_mode="HTML")
                logger.info(f"User {user_id_str} submitted {link_type_msg} for must-join: '{channel_link_input}'. Added directly. State: awaiting_must_join_channels")

        elif state == "awaiting_must_join_public_channel_admin_confirm":
            bot.send_message(message.chat.id, "Please click 'Done, Bot is Admin' for the Public Channel you sent, or type <code>/done</code> to skip and proceed.", parse_mode="HTML")
            logger.info(f"User {user_id_str} sent text in 'awaiting_must_join_public_channel_admin_confirm'. Reminded.")
            return
        elif state == "awaiting_must_join_mandatory_choice":
            bot.send_message(message.chat.id, "Please choose 'Yes' or 'No' for whether joining the channel should be mandatory, using the buttons provided.", parse_mode="HTML")
            logger.info(f"User {user_id_str} sent text in 'awaiting_must_join_mandatory_choice'. Reminded to use buttons.")
            return
        elif state == "awaiting_payment_channel_admin_confirm":
            bot.send_message(message.chat.id, "Please click 'Done, Bot is Admin' for the Payment Channel, or contact support if stuck.", parse_mode="HTML")
            logger.info(f"User {user_id_str} sent text in 'awaiting_payment_channel_admin_confirm'. Reminded.")
            return

        elif state == "awaiting_min_withdrawal":
            try:
                 min_withdrawal_text = message.text.strip().replace(',', '')
                 min_withdrawal = float(min_withdrawal_text)
                 if min_withdrawal < 0:
                     bot.send_message(message.chat.id, "⚠️ Minimum withdrawal cannot be negative.\nE.g., <code>100</code>.", parse_mode="HTML")
                     return
                 user_data[user_id_str]["min_withdrawal"] = min_withdrawal
                 user_states[user_id_str] = "awaiting_max_withdrawal"
                 bot.send_message(message.chat.id, f"Min withdrawal: <b>{min_withdrawal:.2f}</b>\n\n<b>Max withdrawal amount</b> per request? (e.g., <code>1000</code>)", parse_mode="HTML")
                 logger.info(f"User {user_id_str} set min withdrawal to {min_withdrawal}.")
            except ValueError:
                 bot.send_message(message.chat.id, "⚠️ Invalid number for min withdrawal.\nE.g., <code>100</code>.", parse_mode="HTML")

        elif state == "awaiting_max_withdrawal":
            try:
                 max_withdrawal_text = message.text.strip().replace(',', '')
                 max_withdrawal = float(max_withdrawal_text)
                 if max_withdrawal < 0:
                     bot.send_message(message.chat.id, "⚠️ Max withdrawal cannot be negative.\nE.g., <code>1000</code>.", parse_mode="HTML")
                     return
                 if "min_withdrawal" not in user_data.get(user_id_str, {}):
                     logger.error(f"State error for {user_id_str}: max_withdrawal without min_withdrawal.")
                     user_states.pop(user_id_str, None); user_data.pop(user_id_str, None)
                     bot.send_message(message.chat.id, "❌ Error in process. Start over.", reply_markup=main_menu_keyboard(), parse_mode="HTML")
                     return
                 min_withdrawal = user_data[user_id_str]["min_withdrawal"]
                 if max_withdrawal < min_withdrawal:
                     bot.send_message(message.chat.id, f"⚠️ Max withdrawal (<b>{max_withdrawal:.2f}</b>) must be >= min withdrawal (<b>{min_withdrawal:.2f}</b>).\nRe-enter max amount.", parse_mode="HTML")
                     return
                 user_data[user_id_str]["max_withdrawal"] = max_withdrawal
                 user_states[user_id_str] = "awaiting_referral_reward"
                 bot.send_message(message.chat.id, f"Max withdrawal: <b>{max_withdrawal:.2f}</b>\n\nFinally, <b>referral reward amount</b>? (e.g., <code>5</code>, or <code>0</code> for no reward)", parse_mode="HTML")
                 logger.info(f"User {user_id_str} set max withdrawal to {max_withdrawal}.")
            except ValueError:
                 bot.send_message(message.chat.id, "⚠️ Invalid number for max withdrawal.\nE.g., <code>1000</code>.", parse_mode="HTML")

        elif state == "awaiting_referral_reward":
            # --- START FIX ---
            # Isolate the conversion of user input into its own try-except block
            # to ensure the error message is only about the user's number format.
            try:
                referral_reward_text = message.text.strip().replace(',', '')
                referral_reward = float(referral_reward_text)
            except ValueError:
                bot.send_message(message.chat.id, "⚠️ Invalid number for referral reward.\nE.g., <code>5</code> or <code>0</code>.", parse_mode="HTML")
                return # Stop processing if the number is invalid

            # Use a new try-except block for all subsequent logic. If any other error
            # occurs here, it will be caught and logged properly without blaming the user's input.
            try:
                if referral_reward < 0:
                    bot.send_message(message.chat.id, "⚠️ Referral reward cannot be negative.\nE.g., <code>5</code> or <code>0</code>.", parse_mode="HTML")
                    return
                user_data[user_id_str]["referral_reward"] = referral_reward
                logger.info(f"User {user_id_str} set referral reward to {referral_reward}.")

                config_data_str = create_config_data(user_id_str)
                if config_data_str is None:
                    logger.error(f"Failed to generate config for user {user_id_str}.")
                    user_states.pop(user_id_str, None); user_data.pop(user_id_str, None)
                    bot.send_message(message.chat.id, "❌ Internal error finalizing config. Please try again.", reply_markup=main_menu_keyboard(), parse_mode="HTML")
                    return

                database = load_database()
                if user_id_str not in database["users"]: # Should exist from /start
                    logger.warning(f"User {user_id_str} not in DB at end of creation, which is unusual. Registering.")
                    database["users"][user_id_str] = {
                        "username": message.from_user.username if message.from_user.username else "Unknown",
                        "first_name": message.from_user.first_name if message.from_user.first_name else "Unknown",
                        "registration_date": time.strftime("%Y-%m-%d %H:%M:%S"), "bots": []
                    }
                if "bots" not in database["users"][user_id_str]: database["users"][user_id_str]["bots"] = []

                bot_name_final = user_data.get(user_id_str, {}).get("bot_name", "Unnamed Bot")
                bot_username_final = user_data.get(user_id_str, {}).get("bot_username", "UnknownUsername") # Includes @

                new_bot_entry_data = {
                    "bot_name": bot_name_final,
                    "bot_username": bot_username_final, # Stored with @
                    "status": "Pending",
                    "creation_request_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "config_details": config_data_str
                }
                database["users"][user_id_str]["bots"].append(new_bot_entry_data)
                save_database(database) # Save the database
                logger.info(f"Bot {bot_username_final} for user {user_id_str} saved as Pending. DB updated.")

                payment_channel_final = user_data.get(user_id_str, {}).get("payment_channel", "Not Set")
                must_join_channels_final = user_data.get(user_id_str, {}).get("must_join_channels", [])
                
                user_states.pop(user_id_str, None); user_data.pop(user_id_str, None)
                logger.info(f"Cleared state/data for user {user_id_str} post-submission.")
                
                user_conf_msg = (f"✅ <b>Configuration Complete!</b>\n\n"
                                 f"Request for bot <b>{html.escape(bot_name_final)} ({html.escape(bot_username_final)})</b> submitted for review.\n"
                                 f"Notification upon approval (1-12 hours).\n\n"
                                 f"⚠️ <b>IMPORTANT REMINDERS for {html.escape(bot_username_final)} to work correctly:</b>\n")
                if payment_channel_final != "Not Set" and payment_channel_final != "MISSING_PAYMENT_CHANNEL":
                    user_conf_msg += f"1. Your Payment Proof Channel (<code>{html.escape(payment_channel_final)}</code>) needs {html.escape(bot_username_final)} as an <b>admin with post rights</b>.\n"
                
                mandatory_channels_set = [ch['url'] for ch in must_join_channels_final if ch.get('is_public_channel') and ch.get('check')]
                if mandatory_channels_set:
                    user_conf_msg += f"2. For any 'Mandatory Join' Public Telegram Channels you made (e.g., {html.escape(mandatory_channels_set[0])}...), {html.escape(bot_username_final)} must be an <b>admin</b> there to check memberships.\n"
                user_conf_msg += f"Failure to grant these admin rights may cause your bot to not function as expected."
                bot.send_message(message.chat.id, user_conf_msg, reply_markup=main_menu_keyboard(), parse_mode="HTML")

                admin_markup = InlineKeyboardMarkup()
                # Pass bot_username_final (which includes @) to admin callbacks
                admin_markup.row(
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_bot:{user_id_str}:{bot_username_final}"),
                    InlineKeyboardButton("❌ Decline", callback_data=f"decline_bot:{user_id_str}:{bot_username_final}")
                )
                admin_notify_msg = f"🆕 <b>New Bot Creation Request</b>\n\n" \
                            f"<b>From:</b> {html.escape(message.from_user.first_name or 'N/A')} (@{html.escape(message.from_user.username or 'N/A')}, ID: <code>{user_id_str}</code>)\n" \
                            f"<b>Bot Name:</b> {html.escape(bot_name_final)}\n" \
                            f"<b>Bot Username:</b> {html.escape(bot_username_final)}\n\n" \
                            f"<b>Configuration:</b>\n<pre><code class=\"language-python\">{html.escape(config_data_str)}</code></pre>"
                if len(admin_notify_msg) > 4096:
                    cutoff = 4090; admin_notify_msg = admin_notify_msg[:cutoff] + "\n...(truncated)"
                try:
                    bot.send_message(ADMIN_ID, admin_notify_msg, parse_mode="HTML", reply_markup=admin_markup)
                except Exception as e:
                    logger.error(f"CRITICAL: Failed to send request for {bot_username_final} to admin {ADMIN_ID}: {e}", exc_info=True)
                    bot.send_message(message.chat.id, "⚠️ Issue notifying admin. Contact support if bot isn't approved soon.", parse_mode="HTML")
            except Exception as e_inner:
                # This will catch any other errors during the process and provide a better error message.
                logger.error(f"Error occurred after processing referral reward for user {user_id_str}: {e_inner}", exc_info=True)
                bot.send_message(message.chat.id, "❌ An unexpected error occurred while saving your bot configuration. The process has been cancelled. Please try again.", reply_markup=main_menu_keyboard(), parse_mode="HTML")
                # Clean up state to prevent user from being stuck
                user_states.pop(user_id_str, None)
                user_data.pop(user_id_str, None)
            # --- END FIX ---

    except Exception as e:
        user_id_str_err = str(message.from_user.id)
        current_state_err = user_states.get(user_id_str_err, "Unknown")
        logger.error(f"Generic msg error for user {user_id_str_err} in state '{current_state_err}': {e}", exc_info=True)
        if user_id_str_err in user_states: user_states.pop(user_id_str_err, None)
        if user_id_str_err in user_data: user_data.pop(user_id_str_err, None)
        try:
             bot.send_message(message.chat.id, "❌ Unexpected error during bot creation. Progress reset.\nTry again from main menu.", reply_markup=main_menu_keyboard(), parse_mode="HTML")
        except Exception as send_err:
             logger.error(f"Failed to send error msg to user {user_id_str_err}: {send_err}", exc_info=True)


def create_config_data(user_id_str):
    data_cfg = user_data.get(user_id_str)
    if not data_cfg:
         logger.error(f"Config data attempt for user {user_id_str}, but data empty/missing.")
         return None
    logger.debug(f"Generating config for user {user_id_str} with data: {data_cfg}")

    channels_list_str = []
    for channel_item in data_cfg.get('must_join_channels', []):
        url_ch = json.dumps(channel_item.get('url', ''))
        name_ch = json.dumps(channel_item.get('name', 'Unnamed Channel/Group'))
        # 'check' is True if it's a public TG channel AND user selected mandatory
        check_bool_ch = channel_item.get('is_public_channel', False) and channel_item.get('check', False)
        channels_list_str.append(
             f"        {{\n"
             f"            'url': {url_ch},\n"
             f"            'check': {check_bool_ch}, # True if mandatory public TG channel\n"
             f"            'name': {name_ch}\n"
             f"        }}"
        )
    channels_final_str = ',\n'.join(channels_list_str)
    if channels_list_str:
        channels_final_str += '\n'

    bot_token_cfg = data_cfg.get('bot_token', 'MISSING_TOKEN')
    referral_reward_cfg = data_cfg.get('referral_reward', 0.0)
    min_withdrawal_cfg = data_cfg.get('min_withdrawal', 0.0)
    max_withdrawal_cfg = data_cfg.get('max_withdrawal', 1000.0)
    payment_channel_cfg = data_cfg.get('payment_channel', 'MISSING_PAYMENT_CHANNEL')
    bot_username_cfg = data_cfg.get('bot_username', 'MISSING_BOT_USERNAME') # Includes @
    bot_name_cfg = data_cfg.get('bot_name', 'MISSING_BOT_NAME')

    # --- START FIX ---
    # The curly braces for the hardcoded "TASKS" list are now properly escaped 
    # by doubling them (e.g., { becomes {{).
    config_str_out = f"""# Bot Config by BotMaker for User: {user_id_str} | Bot: {bot_username_cfg} #
CONFIG = {{
    "BOT_TOKEN": {json.dumps(bot_token_cfg)},
    "ADMIN_ID": {ADMIN_ID},  # This is the BotMaker's Admin ID
    "REFERRAL_REWARD": {referral_reward_cfg},
    "MIN_WITHDRAWAL": {min_withdrawal_cfg},
    "MAX_WITHDRAWAL": {max_withdrawal_cfg},
    "WITHDRAWAL_ENABLED": True,
    "MUST_JOIN_CHANNELS": [
{channels_final_str}    ],
    "TASKS": [
        {{"name": "Task 1", "url": "https://t.me/tenocoofficial", "reward": 100}}
    ],
    "PAYMENT_CHANNEL": {json.dumps(payment_channel_cfg)},
    "BOT_USERNAME": {json.dumps(bot_username_cfg)}, # Includes @
    "BOT_NAME": {json.dumps(bot_name_cfg)}
}}"""
    # --- END FIX ---
    return config_str_out


@bot.message_handler(commands=['stats'])
def stats_command(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        logger.warning(f"User {message.from_user.id} tried /stats unauthorized.")
        bot.reply_to(message, "⛔ You are not authorized for this command.", parse_mode="HTML")
        return

    database = load_database()
    all_users = database.get("users", {})
    total_users_count = len(all_users)
    total_bots_count = 0
    for user_id_stat in all_users:
        total_bots_count += len(all_users[user_id_stat].get("bots", []))
            
    stats_message = f"📊 <b>BotMaker Statistics</b> 📊\n\n"
    stats_message += f"👥 <b>Total Registered Users:</b> {total_users_count}\n"
    stats_message += f"🤖 <b>Total Bots Created/Requested:</b> {total_bots_count}\n"
    bot.send_message(ADMIN_ID, stats_message, parse_mode="HTML")
    logger.info(f"Admin {ADMIN_ID} requested /stats.")


@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        logger.warning(f"User {message.from_user.id} tried /broadcast unauthorized.")
        bot.reply_to(message, "⛔ You are not authorized.", parse_mode="HTML")
        return
    msg_admin = bot.send_message(message.chat.id, "Admin, send the message to broadcast (text, photo/video with caption).\nType <code>/cancelbroadcast</code> to abort.", parse_mode="HTML")
    bot.register_next_step_handler(msg_admin, process_broadcast_content)

def process_broadcast_content(message):
     if str(message.from_user.id) != str(ADMIN_ID):
         logger.warning(f"Intercepted non-admin msg in broadcast: User {message.from_user.id}")
         return
     if message.text and message.text.lower() == '/cancelbroadcast':
          bot.send_message(ADMIN_ID, "Broadcast cancelled.")
          logger.info("Admin cancelled broadcast via /cancelbroadcast.")
          broadcast_temp_data.pop(str(ADMIN_ID), None)
          return

     text_bc = None; photo_id_bc = None; video_id_bc = None; parse_mode_bc = None
     if message.content_type == 'text':
         text_bc = message.text; parse_mode_bc = "HTML"
     elif message.content_type == 'photo':
         photo_id_bc = message.photo[-1].file_id
         text_bc = message.caption;
         if text_bc: parse_mode_bc = "HTML"
     elif message.content_type == 'video':
         if hasattr(message, 'video') and message.video:
             video_id_bc = message.video.file_id
             text_bc = message.caption
             if text_bc: parse_mode_bc = "HTML"
     if not text_bc and not photo_id_bc and not video_id_bc:
         bot.send_message(ADMIN_ID, "Broadcast cancelled: No content (text, photo, video).")
         return

     broadcast_temp_data[str(ADMIN_ID)] = {
          "text": text_bc, "photo_id": photo_id_bc, "video_id": video_id_bc,
          "parse_mode": parse_mode_bc,
          "original_chat_id": message.chat.id, "original_message_id": message.message_id
     }

     db_bc = load_database()
     user_count_bc = len(db_bc.get("users", {}))
     confirm_msg_bc = f"<b>Broadcast Preview</b>\n(To {user_count_bc} users)\n\n"
     if photo_id_bc: confirm_msg_bc += "[Photo Attached]\n"
     if video_id_bc: confirm_msg_bc += "[Video Attached]\n"
     if text_bc:
         preview_text_bc = html.escape(text_bc)
         confirm_msg_bc += f"<b>Text/Caption:</b>\n{preview_text_bc[:1000]}{'...' if len(preview_text_bc)>1000 else ''}\n\n"
     else: confirm_msg_bc += "(No text caption)\n\n"

     markup_bc = InlineKeyboardMarkup()
     markup_bc.row(InlineKeyboardButton("✅ Confirm & Send", callback_data="confirm_broadcast"),
                   InlineKeyboardButton("❌ Cancel Broadcast", callback_data="cancel_broadcast"))
     try:
          if photo_id_bc:
               bot.send_photo(ADMIN_ID, photo_id_bc, caption=confirm_msg_bc, reply_markup=markup_bc, parse_mode="HTML")
          elif video_id_bc:
               bot.send_video(ADMIN_ID, video_id_bc, caption=confirm_msg_bc, reply_markup=markup_bc, parse_mode="HTML")
          else:
               bot.send_message(ADMIN_ID, confirm_msg_bc, reply_markup=markup_bc, parse_mode="HTML")
          logger.info(f"Sent broadcast confirm preview to admin {ADMIN_ID}.")
     except Exception as e:
          logger.error(f"Failed to send broadcast confirm preview: {e}", exc_info=True)
          bot.send_message(ADMIN_ID, "Error generating preview. Broadcast cancelled.", parse_mode="HTML")
          broadcast_temp_data.pop(str(ADMIN_ID), None)

def send_broadcast_messages(admin_id_bc, text_content, photo_file_id, video_file_id, parse_mode_send):
    db_send = load_database()
    users_send = db_send.get("users", {})
    total_users_send = len(users_send)
    success_s = 0; failed_s = 0; block_s = 0
    logger.info(f"Starting broadcast to {total_users_send} users.")
    status_msg_obj = None
    try:
        status_msg_obj = bot.send_message(admin_id_bc, f"🚀 Broadcasting started...\n\nProcessed: 0 / {total_users_send}\nSent: 0\nFailed: 0\nBlocked: 0", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send initial broadcast status to admin: {e}")

    last_update_s = time.time()
    for i, user_id_s_str in enumerate(list(users_send.keys())):
        try:
            user_id_s = int(user_id_s_str)
            if photo_file_id:
                bot.send_photo(user_id_s, photo_file_id, caption=text_content, parse_mode=parse_mode_send)
            elif video_file_id:
                bot.send_video(user_id_s, video_file_id, caption=text_content, parse_mode=parse_mode_send)
            elif text_content:
                 bot.send_message(user_id_s, text_content, parse_mode=parse_mode_send, disable_web_page_preview=True)
            success_s += 1
        except Exception as e_send:
             error_msg_s = str(e_send).lower()
             if "forbidden: bot was blocked by the user" in error_msg_s or \
                "user is deactivated" in error_msg_s or \
                "chat not found" in error_msg_s or \
                "bot can't initiate conversation" in error_msg_s:
                  block_s += 1
                  logger.warning(f"Broadcast fail user {user_id_s_str} (Blocked/Inactive): {e_send}")
             else:
                  failed_s += 1
                  logger.error(f"Failed broadcast to user {user_id_s_str}: {e_send}", exc_info=False)
        time.sleep(0.05) # Be respectful to Telegram API

        processed_count = i + 1
        if status_msg_obj and (time.time() - last_update_s > 2 or processed_count % 10 == 0 or processed_count == total_users_send) : # Update more frequently
            try:
                 update_text_s = f"Broadcasting...\n\nProcessed: {processed_count} / {total_users_send}\nSent: {success_s}\nFailed: {failed_s}\nBlocked: {block_s}"
                 bot.edit_message_text(update_text_s, chat_id=status_msg_obj.chat.id, message_id=status_msg_obj.message_id, parse_mode="HTML")
                 last_update_s = time.time()
            except telebot.apihelper.ApiTelegramException as edit_e_s: # Catch specific error for message not modified
                if "message is not modified" not in str(edit_e_s).lower():
                    logger.warning(f"Could not update broadcast status: {edit_e_s}")
            except Exception as edit_e_s:
                 logger.warning(f"Could not update broadcast status (general error): {edit_e_s}")


    final_status_s = f"✅ <b>Broadcast Complete!</b>\n\nProcessed: {total_users_send} / {total_users_send}\nSent: {success_s}\nFailed: {failed_s}\nBlocked/Inactive: {block_s}"
    if status_msg_obj:
        try: bot.edit_message_text(final_status_s, chat_id=status_msg_obj.chat.id, message_id=status_msg_obj.message_id, parse_mode="HTML")
        except Exception: # If edit fails, send new message
            bot.send_message(admin_id_bc, final_status_s, parse_mode="HTML")
    else:
        bot.send_message(admin_id_bc, final_status_s, parse_mode="HTML")
    logger.info(f"Broadcast end. Success: {success_s}, Failed: {failed_s}, Blocked: {block_s}")


if __name__ == "__main__":
    logger.info("--- Starting BotMaker Bot ---")
    logger.info(f"Token: ...{TOKEN[-6:]}")
    logger.info(f"Admin ID: {ADMIN_ID}")
    logger.info(f"Database File: {DATABASE_FILE}")
    logger.info(f"Subscription Check Channel: @{CHANNEL_USERNAME}")
    try:
        bot_info_main = bot.get_me()
        logger.info(f"Bot Connection OK: ID={bot_info_main.id}, Name={bot_info_main.first_name}, User=@{bot_info_main.username}")
        logger.info(f"Checking bot admin status in @{CHANNEL_USERNAME}...")
        try:
           member_info_main = bot.get_chat_member(f"@{CHANNEL_USERNAME}", bot_info_main.id)
           logger.info(f"Bot status in @{CHANNEL_USERNAME}: {member_info_main.status}")
           if member_info_main.status not in ['administrator', 'creator']:
               logger.critical(f"CRITICAL WARNING: Bot is NOT an ADMIN in @{CHANNEL_USERNAME}! Subscription check WILL FAIL.")
           else: logger.info(f"Bot has admin rights in @{CHANNEL_USERNAME}.")
        except Exception as admin_check_err_main:
           logger.critical(f"CRITICAL ERROR: Could not verify bot admin status in @{CHANNEL_USERNAME}. Check channel name and bot adminship. Error: {admin_check_err_main}", exc_info=True)
           # Not exiting here, as bot might be used for other things or channel is optional for some features.
    except Exception as conn_err_main:
        logger.critical(f"BOT CONNECTION FAILED! Check Network or Token. Error: {conn_err_main}", exc_info=True)
        exit(1)

    logger.info("Starting bot polling loop...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=30)
        except requests.exceptions.ReadTimeout as rt_main:
             logger.warning(f"Polling ReadTimeout: {rt_main}. Continuing...")
             time.sleep(1)
        except requests.exceptions.ConnectionError as ce_main:
             logger.error(f"Polling ConnectionError: {ce_main}. Retrying in 15s...")
             time.sleep(15)
        except Exception as e_main_poll:
            logger.critical("UNEXPECTED Error in polling loop!", exc_info=True)
            logger.info("Restarting polling in 10s...")
            time.sleep(10)