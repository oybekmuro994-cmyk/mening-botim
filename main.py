import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- SOZLAMALAR ---
# ⚠️ BU YERGA BOT TOKEN VA TELEGRAM ID'INGIZNI YOZING!
BOT_TOKEN = "8834066127:AAFfER4qpxzIibqyoqPWhMB7Buma3z23ssc"
ADMIN_ID = 5588819248
CREATOR_USERNAME = "@bekoo_zz"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- HOLATLAR (STATES) ---
class Registration(StatesGroup):
    waiting_for_phone = State()
    waiting_for_name = State()
    main_menu = State()
    waiting_for_test_code = State()
    solving_test = State()

class AdminStates(StatesGroup):
    waiting_for_test_name = State()
    waiting_for_test_code = State()
    waiting_for_test_answers = State()
    waiting_for_test_file = State()

# --- VAQTINCHALIK BAZA ---
users_db = {}
tests_db = {}
user_answers = {}

# --- KLAVIATURALAR ---
def get_phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Kontaktni ulashish", request_contact=True)]],
        resize_keyboard=True
    )

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🧮 Majburiy matematika dan test ishlash")]],
        resize_keyboard=True
    )

def get_admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Test tuzish")],
            [KeyboardButton(text="🛑 Testni tugatish")]
        ],
        resize_keyboard=True
    )

# --- BOT HANDLERS (MANTIQLARI) ---

# 1. Start bosilganda
@dp.message(F.text == "/start")
async def start_cmd(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        await message.answer("Xush kelibsiz, Admin!", reply_markup=get_admin_menu())
        return

    await message.answer(
        "Telifon raqam orqali royxatdan oting:",
        reply_markup=get_phone_keyboard()
    )
    await state.set_state(Registration.waiting_for_phone)

# 2. Kontaktni ulashganda
@dp.message(Registration.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer(
        "Ism familyangizni kiriting (Masalan: Palonchiyeva Gulchapchap):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Registration.waiting_for_name)

# 3. Ism-familiya kiritilganda
@dp.message(Registration.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext):
    name = message.text
    user_data = await state.get_data()
    phone = user_data.get("phone")
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    
    users_db[message.from_user.id] = {"name": name, "phone": phone, "username": username}
    
    # Adminga foydalanuvchi ma'lumotlarini yuborish
    admin_alert = (
        f"👤 Yangi foydalanuvchi ro'yxatdan o'tdi:\n\n"
        f"📝 Ism/Familiya: {name}\n"
        f"📞 Nomeri: {phone}\n"
        f"🌐 Username: {username}"
    )
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_alert)
    except Exception as e:
        logging.error(f"Xatolik: {e}")

    await message.answer(
        "Ro'yxatdan muvaffaqiyatli o'tdingiz!",
        reply_markup=get_main_menu()
    )
    await state.set_state(Registration.main_menu)

# 4. Test ishlash tugmasi bosilganda
@dp.message(F.text == "🧮 Majburiy matematika dan test ishlash")
async def start_test_process(message: Message, state: FSMContext):
    await message.answer("Test kodini kriting:")
    await state.set_state(Registration.waiting_for_test_code)

# 5. Test kodini tekshirish
@dp.message(Registration.waiting_for_test_code, F.text)
async def verify_test_code(message: Message, state: FSMContext):
    code = message.text
    if code in tests_db:
        test = tests_db[code]
        if not test.get("active", True):
            await message.answer("❌ Bu test admin tomonidan yakunlangan!")
            await state.set_state(Registration.main_menu)
            return

        await message.answer("✅ Kod to'g'ri!")
        await state.update_data(current_test_code=code)
        
        caption_text = f"📋 Test nomi: {test['name']}\n✍️ Test shu odam tomonidan yartilgan: {CREATOR_USERNAME}\n\nJavoblaringizni ketma-ketlikda yuboring (Masalan: abcd...):"
        await message.answer_document(document=test['file_id'], caption=caption_text)
        await state.set_state(Registration.solving_test)
    else:
        await message.answer("❌ Kod noto'g'ri! Iltimos, qaytadan kiriting:")

# 6. Foydalanuvchi javobini olish
@dp.message(Registration.solving_test, F.text)
async def receive_answers(message: Message, state: FSMContext):
    user_answers_text = message.text.lower().strip()
    data = await state.get_data()
    code = data.get("current_test_code")
    
    if code not in user_answers:
        user_answers[code] = {}
    
    user_answers[code][message.from_user.id] = user_answers_text
    
    await message.answer("Javoblaringiz qabul qilindi! Test yakunlangach natijalar e'lon qilinadi.", reply_markup=get_main_menu())
    await state.set_state(Registration.main_menu)


# --- ADMIN FUNKSIYALARI ---

@dp.message(F.text == "➕ Test tuzish", F.from_user.id == ADMIN_ID)
async def admin_create_test(message: Message, state: FSMContext):
    await message.answer("Test ga nom qoyish:")
    await state.set_state(AdminStates.waiting_for_test_name)

@dp.message(AdminStates.waiting_for_test_name, F.from_user.id == ADMIN_ID)
async def admin_save_name(message: Message, state: FSMContext):
    await state.update_data(test_name=message.text)
    await message.answer("Testga kod qoyish (Faqat raqamlar):")
    await state.set_state(AdminStates.waiting_for_test_code)

@dp.message(AdminStates.waiting_for_test_code, F.from_user.id == ADMIN_ID)
async def admin_save_code(message: Message, state: FSMContext):
    await state.update_data(test_code=message.text)
    await message.answer("Test kalitlarini kiriting (Masalan: abcd...):")
    await state.set_state(AdminStates.waiting_for_test_answers)

@dp.message(AdminStates.waiting_for_test_answers, F.from_user.id == ADMIN_ID)
async def admin_save_answers(message: Message, state: FSMContext):
    await state.update_data(correct_answers=message.text.lower().strip())
    await message.answer("Endi test faylini (PDF yoki rasm) yuklang:")
    await state.set_state(AdminStates.waiting_for_test_file)

@dp.message(AdminStates.waiting_for_test_file, F.document, F.from_user.id == ADMIN_ID)
async def admin_save_file(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("test_name")
    code = data.get("test_code")
    keys = data.get("correct_answers")
    file_id = message.document.file_id
    
    tests_db[code] = {
        "name": name,
        "keys": keys,
        "file_id": file_id,
        "active": True
    }
    
    await message.answer(f"🎉 Test muvaffaqiyatli yaratildi!\n\nNom: {name}\nKod: {code}\nMuallif: {CREATOR_USERNAME}", reply_markup=get_admin_menu())
    await state.clear()

@dp.message(F.text == "🛑 Testni tugatish", F.from_user.id == ADMIN_ID)
async def admin_end_test_prompt(message: Message):
    if not tests_db:
        await message.answer("Hozircha hech qanday test yaratilmagan.")
        return
    
    text = "Tugatmoqchi bo'lgan testingiz kodini yozing:\n\n"
    for code, info in tests_db.items():
        if info["active"]:
            text += f"🔹 Kod: `{code}` - {info['name']}\n"
    
    await message.answer(text)

@dp.message(F.from_user.id == ADMIN_ID, F.text.isdigit())
async def admin_finalize_test(message: Message):
    code = message.text
    if code not in tests_db:
        await message.answer("Bunday kodli test topilmadi.")
        return
        
    test = tests_db[code]
    test["active"] = False
    
    correct_keys = test["keys"]
    total_questions = len(correct_keys)
    
    results_text = f"📊 **Test yakunlandi! Natijalar ({test['name']}):**\n\n"
    
    if code in user_answers and user_answers[code]:
        for u_id, u_ans in user_answers[code].items():
            user_info = users_db.get(u_id, {"name": "Noma'lum", "username": ""})
            
            correct_count = 0
            for i in range(min(len(correct_keys), len(u_ans))):
                if u_ans[i] == correct_keys[i]:
                    correct_count += 1
            
            wrong_count = total_questions - correct_count
            percent = (correct_count / total_questions) * 100 if total_questions > 0 else 0
            
            user_report = (
                f"👤 {user_info['name']} ({user_info['username']})\n"
                f"✅ To'g'ri: {correct_count} ta\n"
                f"❌ Xato: {wrong_count} ta\n"
                f"📈 Foiz: {percent:.1f}%\n"
                f"-------------------------\n"
            )
            results_text += user_report
            
            try:
                await bot.send_message(
                    chat_id=u_id, 
                    text=f"📊 **Sizning test natijangiz ({test['name']}):**\n\n✅ To'g'ri: {correct_count} ta\n❌ Xato: {wrong_count} ta\n📈 Foiz: {percent:.1f}%"
                )
            except Exception:
                pass
    else:
        results_text += "Bu testni hech kim topshirmadi."
        
    await message.answer(results_text, reply_markup=get_admin_menu())

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())