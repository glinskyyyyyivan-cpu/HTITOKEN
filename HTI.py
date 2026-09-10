import asyncio
import logging
import sys
import os
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = "8607898774:AAFimwEzUeMN82UJefBTeqT8Zlipsz8eRMA"
ADMIN_USERNAME = "kranikmonster"

dp = Dispatcher()
USER_DB = {}

class WithdrawStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_wallet = State()

class DiceStates(StatesGroup):
    waiting_for_bet = State()

def is_admin(evt) -> bool:
    return evt.from_user.username == ADMIN_USERNAME

def get_main_keyboard(evt) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🚀 Start Mining", callback_data="start_mining")],
        [InlineKeyboardButton(text="🎲 Play Dice", callback_data="open_dice_menu")],
        [InlineKeyboardButton(text="Profile 👤", callback_data="open_profile")]
    ]
    if is_admin(evt):
        buttons.append([InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="open_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def init_user(uid: int, ref_id: int = None):
    if uid not in USER_DB:
        USER_DB[uid] = {"balance": 100, "referrals": 0, "referrer": ref_id}
        if ref_id and ref_id in USER_DB and ref_id != uid:
            USER_DB[ref_id]["referrals"] += 1
            USER_DB[ref_id]["balance"] += 500

@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    args = message.text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    init_user(uid, ref_id)
    text = (
        "👋 <b>Welcome to HTI Miner!</b>\n\n"
        "⛏ Mine HTI tokens directly to your Pool Wallet.\n"
        "⚡ Tap to boost mining speed!\n"
        "🔗 Connect your TON wallet.\n"
        "💰 Hold HTI to upgrade your miner level!\n\n"
        "Click below to start"
    )
    await message.answer(text=text, reply_markup=get_main_keyboard(message))

@dp.callback_query(F.data == "go_to_menu")
async def back_to_menu(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    init_user(cq.from_user.id)
    text = (
        "👋 <b>Welcome to HTI Miner!</b>\n\n"
        "⛏ Mine HTI tokens directly to your Pool Wallet.\n"
        "⚡ Tap to boost mining speed!\n"
        "🔗 Connect your TON wallet.\n"
        "💰 Hold HTI to upgrade your miner level!\n\n"
        "Click below to start"
    )
    await cq.message.answer(text=text, reply_markup=get_main_keyboard(cq))
    await cq.answer()

@dp.callback_query(F.data == "open_dice_menu")
async def open_dice_menu(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    init_user(uid)
    balance = USER_DB[uid]["balance"]
    await cq.message.answer(
        f"🎲 <b>Dice Game Mode</b>\n\nYour Current Balance: <b>{balance} HTI</b>\n\nPlease enter your bet amount:"
    )
    await state.set_state(DiceStates.waiting_for_bet)
    await cq.answer()

@dp.message(DiceStates.waiting_for_bet)
async def process_dice_bet(message: Message, state: FSMContext):
    uid = message.from_user.id
    init_user(uid)
    if not message.text.strip().isdigit():
        await message.answer("❌ Please enter a valid number:")
        return
    bet = int(message.text.strip())
    if bet <= 0:
        await message.answer("❌ Bet must be greater than 0:")
        return
    if USER_DB[uid]["balance"] < bet:
        await message.answer(f"❌ Not enough tokens. Your balance is {USER_DB[uid]['balance']} HTI:")
        return
    await state.update_data(current_bet=bet)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 1 - 3", callback_data="dice_play_1_3"),
         InlineKeyboardButton(text="🔸 4 - 6", callback_data="dice_play_4_6")],
        [InlineKeyboardButton(text="🎲 Odd (Нечетное)", callback_data="dice_play_odd")],
        [InlineKeyboardButton(text="Menu 🔙", callback_data="go_to_menu")]
    ])
    await message.answer(f"💰 Bet accepted: <b>{bet} HTI</b>\nGuess what will roll on the dice:", reply_markup=kb)

@dp.callback_query(F.data.startswith("dice_play_"))
async def play_the_dice(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    init_user(uid)
    data = await state.get_data()
    bet = data.get("current_bet")
    if not bet or USER_DB[uid]["balance"] < bet:
        await cq.message.answer("❌ Session error.", reply_markup=get_main_keyboard(cq))
        await state.clear()
        await cq.answer()
        return
    choice = cq.data.replace("dice_play_", "")
    dice_msg = await cq.message.answer_dice(emoji="🎲")
    dice_value = dice_msg.dice.value
    await asyncio.sleep(2.5)
    
    won = False
    if choice == "1_3" and dice_value in: won = True
    elif choice == "4_6" and dice_value in: won = True
    elif choice == "odd" and dice_value in: won = True
    
    if won:
        USER_DB[uid]["balance"] += bet
        res = f"🎉 <b>You won!</b>\n\nRolled: <b>{dice_value}</b>\nProfit: <b>+{bet} HTI</b>\nBalance: <b>{USER_DB[uid]['balance']} HTI</b>"
    else:
        USER_DB[uid]["balance"] -= bet
        res = f"😭 <b>You lost!</b>\n\nRolled: <b>{dice_value}</b>\nLoss: <b>-{bet} HTI</b>\nBalance: <b>{USER_DB[uid]['balance']} HTI</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Play Again", callback_data="open_dice_menu")],
        [InlineKeyboardButton(text="Menu 🔙", callback_data="go_to_menu")]
    ])
    await cq.message.answer(text=res, reply_markup=kb)
    await state.clear()
    await cq.answer()

@dp.callback_query(F.data == "start_mining")
async def process_mining_press(cq: CallbackQuery):
    text = "Hello\nClick the button below to mine HTI. The more you click, the more tokens you'll get!"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛏ Tap!", callback_data="tap_click")],
        [InlineKeyboardButton(text="Menu 🔙", callback_data="go_to_menu")]
    ])
    await cq.message.answer(text=text, reply_markup=kb)
    await cq.answer()

@dp.callback_query(F.data == "tap_click")
async def process_tap(cq: CallbackQuery):
    uid = cq.from_user.id
    init_user(uid)
    USER_DB[uid]["balance"] += 1
    await cq.answer(text=f"+1 HTI! Total: {USER_DB[uid]['balance']} ⛏", show_alert=False)

@dp.callback_query(F.data == "open_profile")
async def open_profile(cq: CallbackQuery):
    uid = cq.from_user.id
    init_user(uid)
    uname = cq.from_user.username
    disp = f"@{uname}" if uname else f"ID: {uid}"
    ref = f"https://t.me{uid}"
    st = USER_DB[uid]
    text = f"👤 <b>Your Profile</b>\n\n<b>Username/ID:</b> {disp}\n<b>Total HTI Tokens:</b> {st['balance']} HTI\n<b>Friends invited:</b> {st['referrals']}\n\n🔗 <b>Your Referral Link:</b>\n<code>{ref}</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Withdraw 💰", callback_data="start_withdraw")],
        [InlineKeyboardButton(text="Menu 🔙", callback_data="go_to_menu")]
    ])
    await cq.message.answer(text=text, reply_markup=kb)
    await cq.answer()

@dp.callback_query(F.data == "open_admin")
async def open_admin_panel(cq: CallbackQuery):
    if not is_admin(cq): return
    text = f"⚙️ <b>Welcome Admin</b>\n\nTo give tokens, send text message:\n<code>give ID AMOUNT</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Menu 🔙", callback_data="go_to_menu")]])
    await cq.message.answer(text=text, reply_markup=kb)
    await cq.answer()

@dp.message(lambda msg: msg.text and msg.text.lower().startswith("give"))
async def text_give_tokens(message: Message, state: FSMContext):
    if not is_admin(message): return
    await state.clear()
    try:
        args = message.text.split()
        if len(args) != 3: raise ValueError
        tid, amt = int(args[1]), int(args[2])
        init_user(tid)
        USER_DB[tid]["balance"] += amt
        await message.answer(f"✅ Success! Added {amt} HTI to {tid}.\nNew balance: {USER_DB[tid]['balance']} HTI.")
    except Exception:
        await message.answer("❌ Format error. Use: <code>give ID AMOUNT</code>")

@dp.callback_query(F.data == "start_withdraw")
async def withdraw_amount_request(cq: CallbackQuery, state: FSMContext):
    await cq.message.answer("Choose a number from 2500 to 100000")
    await state.set_state(WithdrawStates.waiting_for_amount)
    await cq.answer()

@dp.message(WithdrawStates.waiting_for_amount)
async def process_withdraw_amount(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Please enter a valid number from 2500 to 100000")
        return
    amt = int(message.text.strip())
    if amt < 2500 or amt > 100000:
        await message.answer("Please enter a valid number from 2500 to 100000")
        return
    uid = message.from_user.id
    init_user(uid)
    if USER_DB[uid]["balance"] < amt:
        await message.answer("Not enough tokens.")
        await state.clear()
        return
    await state.update_data(w_amt=amt)
    await message.answer("🔥Send yout TON wallet🔥")
    await state.set_state(WithdrawStates.waiting_for_wallet)

@dp.message(WithdrawStates.waiting_for_wallet)
async def process_withdraw_wallet(message: Message, state: FSMContext):
    w = message.text.strip()
    data = await state.get_data()
    amt = data.get("w_amt")
    uid = message.from_user.id
    USER_DB[uid]["balance"] -= amt
    await message.answer(f"✅ Application accepted!\nAmount: {amt} HTI\nWallet: {w}", reply_markup=get_main_keyboard(message))
    await state.clear()

def run_web_server():
