import os
import json
import time
import threading
import telebot
from telebot import types
import logging
import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "BOT_TOKEN": "",  # Replace with your actual bot token
    "ADMIN_ID": 6341715879,  # Replace with your Telegram ID
    "REFERRAL_REWARD": 50,  # Naira reward for referrals
    "MIN_WITHDRAWAL": 0.02,  # Minimum withdrawal amount
    "MAX_WITHDRAWAL": 200,  # Maximum withdrawal amount
    "WITHDRAWAL_ENABLED": True,  # Set to False to disable withdrawals
    "MUST_JOIN_CHANNELS": [
        {"name": "Telegram Channel", "url": "https://t.me/tenocoofficial", "check": False},
        {"name": "WhatsApp Group 1", "url": "https://chat.whatsapp.com/HaHHnbKmsol7ydJWDMId7h", "check": False},
         {"name": "WhatsApp Channel", "url": "https://whatsapp.com/channel/0029Vb5bMeGL2AU0ydO03l3p", "check": False},
          {"name": "Telegram Group 1", "url": "https://t.me/+-E0CYuv1doszMTVk", "check": False},
        {"name": "Telegram Channel 2", "url": "https://t.me/Lucky_cash_channel", "check": False},
        {"name": "Telegram Channel 3", "url": "https://t.me/AyCryptoz_2", "check": False},
        {"name": "Telegram Channel 4", "url": "https://t.me/KINGROGGISALPHA", "check": False},
        
        {"name": "Mammon's Payment Channel", "url": "https://t.me/mammons_channel", "check": False}
    ],
    
    "TASKS": [
        {"name": "Task 1", "url": "https://t.me/tenocoofficial", "reward": 10},
        {"name": "Task 2", "url": "https://t.me/Lucky_cash_channel", "reward": 15},
         {"name": "Task 3", "url": "https://t.me/AyCryptoz_2", "reward": 15}
    ],
    "PAYMENT_CHANNEL": "https://t.me/mammons_channel",
    "BOT_USERNAME": "@Macleo_bot",
    "BOT_NAME": "Mammon"
}

# File paths
DATABASE_FILE = "database.json"
CONFIG_FILE = "config.json"
STATS_FILE = "stats.json"

# Initialize bot
bot = telebot.TeleBot(CONFIG["BOT_TOKEN"])

# User withdrawal states
user_withdrawal_data = {}

# Ensure files exist
def ensure_files_exist():
    try:
        # Ensure database.json exists
        if not os.path.exists(DATABASE_FILE):
            with open(DATABASE_FILE, 'w') as f:
                json.dump({}, f)
            logger.info(f"Created {DATABASE_FILE}")

        # Ensure config.json exists
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(CONFIG, f, indent=4)
            logger.info(f"Created {CONFIG_FILE}")
        else:
            # Load existing config and ensure it has all required keys
            with open(CONFIG_FILE, 'r') as f:
                existing_config = json.load(f)

            # Check if all required keys exist, otherwise add them
            updated = False
            for key, value in CONFIG.items():
                if key not in existing_config:
                    existing_config[key] = value
                    updated = True

            if updated:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(existing_config, f, indent=4)
                logger.info(f"Updated {CONFIG_FILE} with missing keys")

        # Ensure stats.json exists
        if not os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'w') as f:
                json.dump({
                    "total_users": 0,
                    "messages_received": 0,
                    "messages_sent": 0,
                    "withdrawals": 0,
                    "total_withdrawal_amount": 0,
                    "total_referrals": 0,
                    "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "blocked_users": 0
                }, f)
            logger.info(f"Created {STATS_FILE}")
    except Exception as e:
        logger.error(f"Error ensuring files exist: {e}")

# Load configuration from config.json
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return CONFIG
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return CONFIG

# Save configuration to config.json
def save_config(config_data):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

# Load database from database.json
def load_database():
    try:
        if os.path.exists(DATABASE_FILE):
            with open(DATABASE_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading database: {e}")
        return {}

# Save database to database.json
def save_database(db):
    try:
        with open(DATABASE_FILE, 'w') as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving database: {e}")

# Thread-safe database operations
db_lock = threading.Lock()

def get_user_data(user_id):
    with db_lock:
        db = load_database()
        user_id_str = str(user_id)
        if user_id_str not in db:
            db[user_id_str] = {
                "balance": 0,
                "referrals": [],
                "join_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "withdrawals": []
            }
            save_database(db)
        return db[user_id_str]

def update_user_data(user_id, data):
    with db_lock:
        db = load_database()
        db[str(user_id)] = data
        save_database(db)

# Load stats from stats.json
def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        return {
            "total_users": 0,
            "messages_received": 0,
            "messages_sent": 0,
            "withdrawals": 0,
            "total_withdrawal_amount": 0,
            "total_referrals": 0,
            "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "blocked_users": 0
        }
    except Exception as e:
        logger.error(f"Error loading stats: {e}")
        return {
            "total_users": 0,
            "messages_received": 0,
            "messages_sent": 0,
            "withdrawals": 0,
            "total_withdrawal_amount": 0,
            "total_referrals": 0,
            "start_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "blocked_users": 0
        }

# Save stats to stats.json
def save_stats(stats):
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving stats: {e}")

# Thread-safe stats operations
stats_lock = threading.Lock()

def update_stats(key, value=1, increment=True):
    with stats_lock:
        stats = load_stats()
        if key in stats:
            if increment:
                stats[key] += value
            else:
                stats[key] = value
        save_stats(stats)

# Check if user is a member of a channel
def is_member(user_id, chat_id):
    try:
        # Extract username from URL if it's a full URL
        if chat_id.startswith("@") and "/" not in chat_id:
            channel_username = chat_id
        else:
            # Extract channel username from potentially different formats
            if "/" in chat_id:
                parts = chat_id.split("/")
                channel_username = "@" + parts[-1]
            else:
                channel_username = "@" + chat_id

        member = bot.get_chat_member(channel_username, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

# Create keyboard with channel buttons
def channels_keyboard():
    config = load_config()
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for channel in config["MUST_JOIN_CHANNELS"]:
        buttons.append(types.InlineKeyboardButton(text=channel["name"], url=channel["url"]))

    # Add buttons in groups of 2
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.add(buttons[i], buttons[i + 1])
        else:
            markup.add(buttons[i])

    markup.add(types.InlineKeyboardButton(text="✅ Verify Membership", callback_data="verify_membership"))
    return markup

# Create main menu keyboard
def main_menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(text="👥 Referrals", callback_data="referrals"),
        types.InlineKeyboardButton(text="📝 Tasks", callback_data="tasks")
    )
    markup.add(types.InlineKeyboardButton(text="💰 Withdraw", callback_data="withdraw"))
    return markup

# Create tasks keyboard
def tasks_keyboard():
    config = load_config()
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for i, task in enumerate(config["TASKS"]):
        buttons.append(types.InlineKeyboardButton(text=f"{task['name']} (+{task['reward']}TON )", url=task["url"]))

    # Add buttons in groups of 2
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.add(buttons[i], buttons[i + 1])
        else:
            markup.add(buttons[i])

    markup.add(types.InlineKeyboardButton(text="🔙 Back to Menu", callback_data="main_menu"))
    return markup

# Broadcast command handler
@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    try:
        update_stats("messages_received")
        # Check if user is admin
        if message.from_user.id == CONFIG["ADMIN_ID"]:
            bot.send_message(message.chat.id, "Please send the message you want to broadcast.")
            bot.register_next_step_handler(message, process_broadcast_message)
            update_stats("messages_sent")
        else:
            bot.send_message(message.chat.id, "❌ You are not authorized to use this command.")
            update_stats("messages_sent")
    except Exception as e:
        logger.error(f"Error in broadcast command: {e}")
        try:
            bot.send_message(message.chat.id, "An error occurred while processing the broadcast command.")
            update_stats("messages_sent")
        except:
            pass

def process_broadcast_message(message):
    try:
        update_stats("messages_received")
        broadcast_content = message
        db = load_database()
        user_ids = list(db.keys())
        successful_broadcasts = 0
        failed_broadcasts = 0
        blocked_users_count = 0

        for user_id in user_ids:
            try:
                if user_id.isdigit():
                    user_id_int = int(user_id)
                    if broadcast_content.text:
                        bot.send_message(user_id_int, broadcast_content.text)
                    elif broadcast_content.photo:
                        photo_id = broadcast_content.photo[-1].file_id
                        caption = broadcast_content.caption
                        bot.send_photo(user_id_int, photo_id, caption=caption)
                    elif broadcast_content.video:
                        video_id = broadcast_content.video.file_id
                        caption = broadcast_content.caption
                        bot.send_video(user_id_int, video_id, caption=caption)
                    elif broadcast_content.forward_from_chat:
                        bot.forward_message(user_id_int, broadcast_content.forward_from_chat.id, broadcast_content.forward_from_message_id)
                    elif broadcast_content.forward_from:
                        bot.forward_message(user_id_int, broadcast_content.chat.id, broadcast_content.message_id) # Handle forwarded messages from users
                    else:
                        bot.send_message(message.chat.id, f"Unsupported broadcast content type.") # Notify admin about unsupported type
                        return

                    successful_broadcasts += 1
                    time.sleep(0.05) # Add a small delay to avoid rate limiting
                    update_stats("messages_sent")
                else:
                    logger.warning(f"Skipping non-integer user ID: {user_id}")
                    failed_broadcasts += 1 # Increment failed count for non-integer IDs
            except telebot.apihelper.ApiTelegramException as e:
                if e.result_json and e.result_json.get('description') == 'Forbidden: bot was blocked by the user':
                    logger.warning(f"Bot blocked by user {user_id_int}")
                    blocked_users_count += 1
                else:
                    logger.error(f"Failed to broadcast to user {user_id_int}: {e}")
                failed_broadcasts += 1
            except Exception as e:
                logger.error(f"An unexpected error occurred while broadcasting to user {user_id}: {e}")
                failed_broadcasts += 1

        total_users = len(db)
        active_users = total_users - blocked_users_count

        bot.send_message(message.chat.id, f"Broadcast completed.\nSuccessful: {successful_broadcasts}\nFailed: {failed_broadcasts}\nUsers who blocked the bot: {blocked_users_count}\nActive users remaining: {active_users}")
        update_stats("messages_sent")
        update_stats("blocked_users", blocked_users_count) # Update blocked users count in stats
    except Exception as e:
        logger.error(f"Error processing broadcast message: {e}")
        try:
            bot.send_message(message.chat.id, "An error occurred while processing the broadcast.")
            update_stats("messages_sent")
        except:
            pass

# Start command handler
@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        update_stats("messages_received")
        user_id = message.from_user.id
        username = message.from_user.username or f"user{user_id}"
        user_data = get_user_data(user_id)

        # Check if this is a referral
        if len(message.text.split()) > 1:
            try:
                referrer_id = message.text.split()[1]
                if referrer_id.isdigit() and str(user_id) != referrer_id:
                    referrer_data = get_user_data(referrer_id)
                    if str(user_id) not in referrer_data["referrals"]:
                        config = load_config()
                        referral_reward = config["REFERRAL_REWARD"]

                        # Add referral to referrer's list
                        referrer_data["referrals"].append(str(user_id))
                        referrer_data["balance"] += referral_reward
                        update_user_data(referrer_id, referrer_data)

                        # Update stats
                        update_stats("total_referrals")

                        # Notify referrer
                        try:
                            bot.send_message(
                                int(referrer_id),
                                f"🎉 Congratulations! You have a new referral: @{username}\n"
                                f"You earned {referral_reward}TON !"
                            )
                            update_stats("messages_sent")
                        except Exception as e:
                            logger.error(f"Error sending referral notification: {e}")
            except Exception as e:
                logger.error(f"Error processing referral: {e}")

        # Count new user
        with db_lock:
            db = load_database()
            if str(user_id) not in db:
                update_stats("total_users")

        # Send join channels message
        welcome_text = (
            f"👋 Hello, @{username}!\n\n"
            f"Please join our channels and groups to continue:\n\n"
           
        )

        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=channels_keyboard(),
            parse_mode="HTML"
        )
        update_stats("messages_sent")

    except Exception as e:
        logger.error(f"Error in start command: {e}")
        try:
            bot.send_message(message.chat.id, "An error occurred. Please try again.")
            update_stats("messages_sent")
        except:
            pass

# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        user_id = call.from_user.id
        username = call.from_user.username or f"user{user_id}"
        user_data = get_user_data(user_id)
        config = load_config()  # Reload config for every callback to get latest settings

        # Handle verification callback
        if call.data == "verify_membership":
            # Check required channels
            required_channels = [ch for ch in config["MUST_JOIN_CHANNELS"] if ch["check"]]
            all_joined = True

            for channel in required_channels:
                channel_name = channel["url"].split("/")[-1]
                try:
                    if not is_member(user_id, channel_name):
                        all_joined = False
                        break
                except Exception as e:
                    logger.error(f"Error in verification: {e}")
                    all_joined = False
                    break

            if all_joined:
                # User joined all required channels, show main menu
                welcome_text = (
                    f"✅ Verification successful!\n\n"
                    f"👋 Welcome to {config['BOT_NAME']}, @{username}!\n\n"
                    f"💰 Your Balance: {user_data['balance']}TON \n\n"
                    f"Please select an option below:"
                )

                bot.edit_message_text(
                    welcome_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=main_menu_keyboard(),
                    parse_mode="HTML"
                )
                update_stats("messages_sent")
            else:
                # User hasn't joined all required channels
                bot.answer_callback_query(
                    call.id,
                    "❌ You need to join all the required channels to continue or the bot may not be an admin in the Telegram channel.",
                    show_alert=True
                )

        # Handle main menu callback
        elif call.data == "main_menu":
            welcome_text = (
                f"👋 Welcome back, @{username}!\n\n"
                f"💰 Your Balance: {user_data['balance']}TON \n\n"
                f"Please select an option below:"
            )

            bot.edit_message_text(
                welcome_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )
            update_stats("messages_sent")

        # Handle referrals callback
        elif call.data == "referrals":
            referral_link = f"https://t.me/{config['BOT_USERNAME'].replace('@', '')}?start={user_id}"
            referral_count = len(user_data["referrals"])
            referral_reward = config["REFERRAL_REWARD"]

            referral_text = (
                f"👥 Your Referrals: {referral_count}\n\n"
                f"💰 Earn {referral_reward}TON  for each new referral!\n\n"
                f"🔗 Your Referral Link:\n"
                f"{referral_link}\n\n"
                f"Share this link with friends and earn money when they join!"
            )

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="🔙 Back to Menu", callback_data="main_menu"))

            bot.edit_message_text(
                referral_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML"
            )
            update_stats("messages_sent")

        # Handle tasks callback
        elif call.data == "tasks":
            tasks_text = (
                f"📝 Available Tasks\n\n"
                f"Complete these tasks to earn rewards:"
            )

            bot.edit_message_text(
                tasks_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=tasks_keyboard(),
                parse_mode="HTML"
            )
            update_stats("messages_sent")

        # Handle withdraw callback
        elif call.data == "withdraw":
            if not config["WITHDRAWAL_ENABLED"]:
                bot.answer_callback_query(call.id, "❌ Withdrawals are currently disabled.", show_alert=True)
                return

            withdraw_text = (
                f"💰 Withdrawal\n\n"
                f"Your Balance: {user_data['balance']}TON \n\n"
                f"Minimum Withdrawal: {config['MIN_WITHDRAWAL']}TON \n"
                f"Please enter the amount you want to withdraw:"
            )

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="🔙 Back to Menu", callback_data="main_menu"))

            bot.edit_message_text(
                withdraw_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML"
            )
            update_stats("messages_sent")

            # Register next step handler for withdrawal amount
            bot.register_next_step_handler(call.message, process_withdrawal_amount)

    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        try:
            bot.answer_callback_query(call.id, "An error occurred. Please try again.")
        except:
            pass

# Process withdrawal amount
def process_withdrawal_amount(message):
    try:
        update_stats("messages_received")
        user_id = message.from_user.id
        username = message.from_user.username or f"user{user_id}"
        user_data = get_user_data(user_id)
        config = load_config()

        # Check if message is a valid number (allow floats)
        try:
            amount = float(message.text)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Please enter a valid number.",
                reply_markup=main_menu_keyboard()
            )
            update_stats("messages_sent")
            return

        # Check minimum and maximum withdrawal
        if amount < config["MIN_WITHDRAWAL"]:
            bot.send_message(
                message.chat.id,
                f"❌ Minimum withdrawal amount is {config['MIN_WITHDRAWAL']} TON.",
                reply_markup=main_menu_keyboard()
            )
            update_stats("messages_sent")
            return

        if amount > config["MAX_WITHDRAWAL"]:
            bot.send_message(
                message.chat.id,
                f"❌ Maximum withdrawal amount is {config['MAX_WITHDRAWAL']} TON.",
                reply_markup=main_menu_keyboard()
            )
            update_stats("messages_sent")
            return

        # Check user balance
        if amount > user_data["balance"]:
            bot.send_message(
                message.chat.id,
                f"❌ Insufficient balance. Your balance is {user_data['balance']} TON.",
                reply_markup=main_menu_keyboard()
            )
            update_stats("messages_sent")
            return

        # Store withdrawal amount and ask for account number
        user_withdrawal_data[user_id] = {"amount": amount}
        bot.send_message(
            message.chat.id,
            "Please enter your TON address:"
        )
        bot.register_next_step_handler(message, process_withdrawal_account_number)

    except Exception as e:
        logger.error(f"Error processing withdrawal amount: {e}")
        try:
            bot.send_message(message.chat.id, "An error occurred. Please try again.")
            update_stats("messages_sent")
        except:
            pass

# Process withdrawal account number
def process_withdrawal_account_number(message):
    try:
        update_stats("messages_received")
        user_id = message.from_user.id
        account_number = message.text

        if user_id not in user_withdrawal_data:
            bot.send_message(message.chat.id, "❌ Something went wrong. Please try the withdrawal again.")
            return

        user_withdrawal_data[user_id]["account_number"] = account_number
        bot.send_message(
            message.chat.id,
            "Please send the name of your wallet:"
        )
        bot.register_next_step_handler(message, process_withdrawal_bank_name)

    except Exception as e:
        logger.error(f"Error processing withdrawal account number: {e}")
        try:
            bot.send_message(message.chat.id, "An error occurred. Please try again.")
            update_stats("messages_sent")
        except:
            pass

# Process withdrawal bank name
def process_withdrawal_bank_name(message):
    try:
        update_stats("messages_received")
        user_id = message.from_user.id
        username = message.from_user.username or f"user{user_id}"
        user_data = get_user_data(user_id)
        config = load_config()
        bank_name = message.text

        if user_id not in user_withdrawal_data or "amount" not in user_withdrawal_data[user_id] or "account_number" not in user_withdrawal_data[user_id]:
            bot.send_message(message.chat.id, "❌ Something went wrong. Please try the withdrawal again.")
            return

        amount = user_withdrawal_data[user_id]["amount"]
        account_number = user_withdrawal_data[user_id]["account_number"]

        # Process withdrawal
        user_data["balance"] -= amount

        # Record withdrawal in user data
        withdrawal_record = {
            "amount": amount,
            "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending",
            "account_number": account_number,
            "bank_name": bank_name
        }

        if "withdrawals" not in user_data:
            user_data["withdrawals"] = []

        user_data["withdrawals"].append(withdrawal_record)
        update_user_data(user_id, user_data)

        # Send withdrawal request to payment channel
        try:
            payment_channel = CONFIG["PAYMENT_CHANNEL"]
            if payment_channel.startswith("https://t.me/"):
                channel_username = payment_channel.split("/")[-1]
                if not channel_username.startswith("@"):
                    channel_username = "@" + channel_username
                bot.send_message(
                    channel_username,
                    f"✅ New Withdrawal Paid!\n\n"
                    f"👤 User: @{username} ({user_id})\n"
                    f"🏦 Wallet: {bank_name}\n"
                    f"💳 Address: <code>{account_number}</code>\n"
                    f"💎 Amount: {amount}TON \n"
                    f"👥 Total Referrals: {len(user_data['referrals'])}\n\n"
                    f"Bot: {config['BOT_USERNAME']}",
                    parse_mode="HTML"
                )
            else:
                # Assume it's already a username or chat ID
                bot.send_message(
                    payment_channel,
                    f"💰 New Withdrawal Request!\n\n"
                    f"👤 User: @{username} (ID: {user_id})\n"
                    f"🏦 Wallet: {bank_name}\n"
                    f"💳 Address: <code>{account_number}</code>\n"
                    f"💎 Amount: {amount}TON \n"
                    f"👥 Total Referrals: {len(user_data['referrals'])}\n\n"
                    f"Bot: {config['BOT_USERNAME']}",
                    parse_mode="HTML"
                )
            update_stats("messages_sent")
        except Exception as e:
            logger.error(f"Error sending withdrawal request to channel: {e}")

        # Notify user
        success_message = (
            f"✅ Withdrawal Request Submitted!\n\n"
            f"💎 Amount: {amount}TON \n"
            f"🏦 Wallet: {bank_name}\n"
            f"💳 TON Address: {account_number}\n"
            f"⏱️ Processing Time: 1-12 hours\n\n"
            f"Your payment will be processed soon. Looting, having multiple accounts, or any form of cheating will result in your withdrawal not being approved. You can check status in our payment channel:\n"
            f"{CONFIG['PAYMENT_CHANNEL']}"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="📢 Payment Channel", url=CONFIG["PAYMENT_CHANNEL"]))
        markup.add(types.InlineKeyboardButton(text="🔙 Back to Menu", callback_data="main_menu"))

        bot.send_message(
            message.chat.id,
            success_message,
            reply_markup=markup,
            parse_mode="HTML"
        )
        update_stats("messages_sent")

        # Clear user withdrawal data
        if user_id in user_withdrawal_data:
            del user_withdrawal_data[user_id]

    except Exception as e:
        logger.error(f"Error processing withdrawal bank name: {e}")
        try:
            bot.send_message(message.chat.id, "An error occurred. Please try again.")
            update_stats("messages_sent")
        except:
            pass

# Stats command handler
@bot.message_handler(commands=['stats'])
def stats_command(message):
    try:
        update_stats("messages_received")

        # Check if user is admin
        if message.from_user.id != CONFIG["ADMIN_ID"]:
            bot.send_message(message.chat.id, "❌ You don't have permission to use this command.")
            update_stats("messages_sent")
            return

        stats = load_stats()
        db = load_database()

        # Calculate additional stats
        active_users = len(db) - stats.get('blocked_users', 0)
        total_balance = 0
        for user_data in db.values():
            if 'balance' in user_data:
                total_balance += user_data['balance']

        # Format start date
        start_date = stats.get("start_date", "N/A")
        if start_date != "N/A":
            try:
                start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
                now = datetime.datetime.now(datetime.timezone.utc)
                days_running = (now - start_date_obj).days
            except ValueError as e:
                logger.error(f"Error parsing start date: {e}")
                days_running = "N/A"
        else:
            days_running = "N/A"

        stats_text = (
            f"📊 Bot Statistics\n\n"
            f"👤 Total Users: {len(db)}\n"
            f"✅ Active Users (Did not block): {active_users}\n"
            f"🚫 Blocked Users: {stats.get('blocked_users', 0)}\n"
            f"🔄 Total Referrals: {stats.get('total_referrals', 0)}\n"
            f"💎 Total Payouts: {total_balance}TON \n"
        )
        if days_running != "N/A":
            stats_text += f"⏳ Bot Running For: {days_running} days\n"

        bot.send_message(message.chat.id, stats_text, parse_mode="HTML")
        update_stats("messages_sent")

    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        try:
            bot.send_message(message.chat.id, "An error occurred. Please try again.")
            update_stats("messages_sent")
        except:
            pass

# Handle all text messages (for debugging and fallback)
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        update_stats("messages_received")

        # Just redirect to main menu
        user_id = message.from_user.id
        username = message.from_user.username or f"user{user_id}"
        user_data = get_user_data(user_id)

        welcome_text = (
            f"👋 Hi @{username}!\n\n"
            f"💰 Your Balance: {user_data['balance']}TON \n\n"
            f"Please select an option below:"
        )

        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        update_stats("messages_sent")

    except Exception as e:
        logger.error(f"Error in message handler: {e}")
        try:
            bot.send_message(message.chat.id, "An error occurred. Please try again.")
            update_stats("messages_sent")
        except:
            pass

# Print all config variables for debugging
def print_config():
    try:
        logger.info("Current configuration:")
        config = load_config()
        for key, value in config.items():
            if key == "MUST_JOIN_CHANNELS":
                logger.info(f"{key}: {len(value)} channels configured")
            else:
                logger.info(f"{key}: {value}")
    except Exception as e:
        logger.error(f"Error printing config: {e}")

# Main function
def main():
    try:
        # Ensure all required files exist
        ensure_files_exist()

        # Print config for debugging
        print_config()

        logger.info("Starting bot...")
        bot.remove_webhook()
        bot.polling(none_stop=True, interval=0, timeout=60)
    except Exception as e:
        logger.error(f"Critical error: {e}")
        time.sleep(10)  # Wait before retrying
        main()  # Restart bot

if __name__ == "__main__":
    main()
    