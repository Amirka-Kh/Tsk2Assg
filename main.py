import logging
import random
import sys
import copy

from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, PicklePersistence
import telegram.ext.filters as filters
from telegram import Update

DATA_FILE = "data"

tasks = {
    '1': 'change trash',
    '2': 'throw trash',
    '3': 'change water',
    '4': 'buy toilet paper',
    '5': 'sweep the kitchen floor',
    '6': 'clean washing table in kitchen',
    '7': 'clean tables in kitchen',
    '8': 'clean the plate',
}
usernames = {}


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


# Upload saved data if exist so and update usernames from input
async def update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    for user in input_usernames:
        if user in usernames[chat_id]:
            continue
        usernames[chat_id].append(user)
    await context.bot.send_message(chat_id=chat_id, text="context and usernames are updated")


# Define a function to add the username of a member when they join the group
async def add_username(update, context):
    chat_id = update.message.chat_id
    username = update.message.from_user.username
    for task in tasks.values():
        if task in context.chat_data.get(chat_id, {}):
            if not context.chat_data[chat_id][task]:
                break
            if context.chat_data[chat_id][task]['members']:
                context.chat_data[chat_id][task]['members'].append(username)
    usernames[chat_id] = usernames.get(chat_id, []) + [username]


# Define a function to remove the username of a member when they leave the group
async def remove_username(update, context):
    chat_id = update.message.chat_id
    username = update.message.left_chat_member.username
    for task in tasks.values():
        if task in context.chat_data.get(chat_id, {}):
            if not context.chat_data[chat_id][task]:
                break
            context.chat_data[chat_id][task]['members'].remove(username)
            if context.chat_data[chat_id][task]['username'] == username:
                context.chat_data[chat_id][task]['username'] = None
                context.chat_data[chat_id][task]['active'] = False
    if chat_id in usernames:
        if username in usernames[chat_id]:
            usernames[chat_id].remove(username)


# Define a function to handle the /usernames command and send the list of usernames
async def list_usernames(update, context):
    chat_id = update.message.chat_id
    if chat_id in usernames:
        message = "List of usernames:\n" + "\n".join(usernames[chat_id])
    else:
        message = "No usernames found"
    await context.bot.send_message(chat_id=chat_id, text=message)


async def show_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = 'Here is the list of available tasks:\n\n'
    for key, task in tasks.items():
        text += f" {key} - {task}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def assign_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    task = tasks[update.message.text[8:9]]
    if task in context.chat_data.get(chat_id, {'members': [], 'active': False, 'username': None}):
        if context.chat_data[chat_id][task]['active']:
            await context.bot.send_message(chat_id=chat_id, text=f'{context.chat_data[chat_id][task]["username"]} '
                                                                 f'already assigned to this task')
            return
        assigned_members_username = context.chat_data[chat_id][task]['members']
        if not context.chat_data[chat_id][task]['members']:
            assigned_members_username = copy.deepcopy(usernames.get(chat_id, {}))
    else:
        assigned_members_username = copy.deepcopy(usernames.get(chat_id, {}))
    if not assigned_members_username:
        await context.bot.send_message(chat_id=chat_id, text=f'There are no user to assign a task')
        return
    responsible_for_task = random.choice(assigned_members_username)
    if chat_id not in context.chat_data:
        context.chat_data[chat_id] = {task: {}}
    if task not in context.chat_data[chat_id]:
        context.chat_data[chat_id][task] = {}
    context.chat_data[chat_id][task]['members'] = assigned_members_username
    context.chat_data[chat_id][task]['active'] = True
    context.chat_data[chat_id][task]['username'] = responsible_for_task
    await context.bot.send_message(chat_id=chat_id, text=f'@{responsible_for_task} has been assigned to {task}.')


async def mark_task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    task = tasks[update.message.text[6:7]]
    if task in context.chat_data.get(chat_id, {}).keys():
        if not context.chat_data[chat_id][task]['active']:
            await context.bot.send_message(chat_id=chat_id, text=f'No user was assigned to a task')
            return
        assigned_members_username = context.chat_data[chat_id][task]['members']
        if update.message.from_user.username in assigned_members_username:
            context.chat_data[chat_id][task]['members'].remove(update.message.from_user.username)
            context.chat_data[chat_id][task]['active'] = False
            context.chat_data[chat_id][task]['username'] = None
            await context.bot.send_message(chat_id=chat_id,
                                           text=f'{update.message.from_user.first_name} has marked {task} as done.')
        else:
            await context.bot.send_message(chat_id=chat_id, text=f'You are not assigned to {task}.')
    else:
        await context.bot.send_message(chat_id=chat_id, text=f'{update.message.text[6:]} is not a valid task.')


if __name__ == '__main__':
    TELEGRAM_TOKEN = sys.argv[1]
    input_usernames = sys.argv[2:]

    my_persistence = PicklePersistence(filepath=DATA_FILE)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).persistence(persistence=my_persistence).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('update', update))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, add_username))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, remove_username))
    app.add_handler(CommandHandler("usernames", list_usernames))
    app.add_handler(CommandHandler('show', show_task))
    app.add_handler(CommandHandler('assign', assign_task))
    app.add_handler(CommandHandler('done', mark_task_done))

    app.run_polling(allowed_updates=Update.ALL_TYPES)
