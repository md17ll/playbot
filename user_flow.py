from telegram import Update
from telegram.ext import ContextTypes

import texts
import keyboards
from utils import (
    safe_edit_or_send,
    nav_push,
    nav_pop,
    nav_reset,
    nav_current
)


# ======================
# HOME
# ======================

async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_reset(context)

    await safe_edit_or_send(
        update,
        context,
        texts.START_MESSAGE,
        keyboards.kb_home(update.effective_user.id)
    )


# ======================
# SHOP
# ======================

async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "shop")

    await safe_edit_or_send(
        update,
        context,
        texts.SHOP_MESSAGE,
        keyboards.kb_shop()
    )


# ======================
# SUBSCRIPTIONS
# ======================

async def show_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "subscriptions")

    await safe_edit_or_send(
        update,
        context,
        texts.SUBSCRIPTIONS_MESSAGE,
        keyboards.kb_subscriptions()
    )


# ======================
# GAMES
# ======================

async def show_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "games")

    await safe_edit_or_send(
        update,
        context,
        texts.GAMES_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# BALANCE
# ======================

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "balance")

    await safe_edit_or_send(
        update,
        context,
        texts.BALANCE_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# COUPON
# ======================

async def show_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "coupon")

    await safe_edit_or_send(
        update,
        context,
        texts.COUPON_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# REFERRAL
# ======================

async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "referral")

    await safe_edit_or_send(
        update,
        context,
        texts.REFERRAL_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# ORDERS
# ======================

async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "orders")

    await safe_edit_or_send(
        update,
        context,
        texts.ORDERS_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# BACK
# ======================

async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):

    state = nav_pop(context)

    if state == "home":
        await safe_edit_or_send(
            update,
            context,
            texts.START_MESSAGE,
            keyboards.kb_home(update.effective_user.id)
        )

    elif state == "shop":
        await safe_edit_or_send(
            update,
            context,
            texts.SHOP_MESSAGE,
            keyboards.kb_shop()
        )

    elif state == "subscriptions":
        await safe_edit_or_send(
            update,
            context,
            texts.SUBSCRIPTIONS_MESSAGE,
            keyboards.kb_subscriptions()
        )

    elif state == "games":
        await safe_edit_or_send(
            update,
            context,
            texts.GAMES_MESSAGE,
            keyboards.kb_back()
        )

    elif state == "balance":
        await safe_edit_or_send(
            update,
            context,
            texts.BALANCE_MESSAGE,
            keyboards.kb_back()
        )

    elif state == "coupon":
        await safe_edit_or_send(
            update,
            context,
            texts.COUPON_MESSAGE,
            keyboards.kb_back()
        )

    elif state == "referral":
        await safe_edit_or_send(
            update,
            context,
            texts.REFERRAL_MESSAGE,
            keyboards.kb_back()
        )

    elif state == "orders":
        await safe_edit_or_send(
            update,
            context,
            texts.ORDERS_MESSAGE,
            keyboards.kb_back()
        )

    else:
        await safe_edit_or_send(
            update,
            context,
            texts.START_MESSAGE,
            keyboards.kb_home(update.effective_user.id)
        )
