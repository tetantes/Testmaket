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

TOKEN = "" # Replace with your actual token
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 6341715879 # Replace with your actual Admin ID
CHANNEL_USERNAME = "tenocobotmaker" # Replace with your actual channel username
CHANNEL_LINK = "https://t.me/tenocobotmaker" # Replace with your actual channel link
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

# user_states is kept for potential future use or for features like broadcast confirmation
user_states = {}
# user_data is kept for potential future use
user_data = {}
broadcast_temp_data = {}

def join_channel_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("➡️ Join Channel", url=CHANNEL_LINK))
    markup.row(InlineKeyboardButton("✅ Continue", callback_data="check_subscription"))
    return markup

def main_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🤖 Create bot", callback_data="create_bot_options"))
    # "My bots" button removed
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
                # "bots": [] removed as this bot no longer manages user-created bots
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
        welcome_msg += "I can help you find resources to create your Telegram bots.\n\n" # Modified text
        welcome_msg += "Please select an option from the menu below:"
        bot.send_message(chat_id, welcome_msg, reply_markup=main_menu_keyboard(), parse_mode="HTML")
        logger.info(f"Sent welcome message and main menu to user {user_id_str}.")
    except Exception as e:
        logger.error(f"Error during welcome message sending/user registration for {user_id_str}: {e}", exc_info=True)
        try:
            bot.send_message(chat_id, "An error occurred while processing your request.\n\nPlease try again later.")
        except Exception as send_error:
             logger.error(f"Failed even to send error message to chat {chat_id}: {send_error}", exc_info=True)

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
                    welcome_msg += "I can help you find resources to create your Telegram bots.\n\n" # Modified text
                    welcome_msg += "Please select an option from the menu below:"
                    bot.edit_message_text(welcome_msg, call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard(), parse_mode="HTML")
                    database = load_database()
                    if user_id_str not in database["users"]:
                         logger.info(f"New user detected post-subscription: {first_name or 'N/A'} (@{username or 'N/A'}, ID: {user_id_str}). Registering.")
                         database["users"][user_id_str] = {
                             "username": username if username else "Unknown",
                             "first_name": first_name if first_name else "Unknown",
                             "registration_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                             # "bots": [] removed
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

    try:
        if call.data == "create_bot_options":
            bot.answer_callback_query(call.id)
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("💵 Naira Bot", url="https://t.me/tenoconairamaker_bot?start=start"),
                InlineKeyboardButton("💎 TON Bot", url="https://t.me/tenocotonmaker_bot?start=start"),
                InlineKeyboardButton("🌟 Star React Bot", url="https://t.me/tenocostarmaker_bot?start=start")
            )
            markup.row(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"))
            bot.edit_message_text(
                "Select a bot type you'd like to create. You'll be redirected to the respective bot maker:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML"
            )
            logger.info(f"User {user_id_str} requested bot creation options.")

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
            # "Bots Created" line removed
            msg += "\nFor support, contact @tenocobot\n" # Placeholder
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

        else:
            # Fallback for unhandled callbacks
            known_exact_matches = ["check_subscription", "confirm_broadcast",
                                   "cancel_broadcast", "create_bot_options",
                                   "my_account", "back_to_main"]
            if call.data not in known_exact_matches:
                 logger.warning(f"Unhandled callback in general try-except: '{call.data}' from user {user_id_str}")
                 try: bot.answer_callback_query(call.id, "Action not recognized or is currently unavailable.")
                 except Exception: pass
    except Exception as e:
        logger.error(f"Generic callback error for callback '{call.data}', user {user_id}: {e}", exc_info=True)
        try: bot.answer_callback_query(call.id, "An internal error occurred. Please try again.", show_alert=True)
        except Exception: pass


# Removed handle_bot_creation(message) function as bot creation logic is removed.
# Removed create_config_data(user_id_str) function.
# Removed validate_bot_token(token) function.
# Removed get_chat_info_from_link(link) function.

@bot.message_handler(commands=['stats'])
def stats_command(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        logger.warning(f"User {message.from_user.id} tried /stats unauthorized.")
        bot.reply_to(message, "⛔ You are not authorized for this command.", parse_mode="HTML")
        return

    database = load_database()
    all_users = database.get("users", {})
    total_users_count = len(all_users)
    # total_bots_count removed
            
    stats_message = f"📊 <b>BotMaker Statistics</b> 📊\n\n"
    stats_message += f"👥 <b>Total Registered Users:</b> {total_users_count}\n"
    # Line for total_bots_count removed
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