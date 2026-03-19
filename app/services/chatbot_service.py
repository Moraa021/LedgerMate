import re
from datetime import datetime, timedelta
from app.models import Transaction, Category
from flask_login import current_user
from sqlalchemy import func

class ChatbotService:
    """Simple rule-based chatbot for helping users with LedgerMate"""
    
    def __init__(self):
        self.intents = {
            'greeting': ['hello', 'hi', 'hey', 'jambo', 'habari', 'hujambo', 'sasa', 'mambo'],
            'add_transaction': ['how to add', 'add transaction', 'record transaction', 'new transaction', 
                               'ongeza muamala', 'rekodi', 'muamala mpya', 'how do i add'],
            'view_report': ['view report', 'see report', 'check report', 'tazama ripoti', 
                           'ripoti', 'show report', 'generate report', 'tengeneza ripoti'],
            'mpesa': ['mpesa', 'mobile money', 'record mpesa', 'rekodi mpesa', 
                     'mpesa code', 'confirmation code', 'nambari ya mpesa'],
            'category': ['category', 'categories', 'aina', 'kategoria', 'group', 
                        'kundi', 'classify', 'ainisha'],
            'delete': ['delete', 'remove', 'futa', 'ondoa', 'cancel', 'ghairi'],
            'export': ['export', 'download', 'print', 'hamisha', 'chapisha', 
                      'pdf', 'csv', 'excel', 'save data'],
            'balance': ['balance', 'net', 'profit', 'loss', 'usalia', 'faida', 
                       'hasara', 'total', 'jumla', 'how much', 'kiasi'],
            'dashboard': ['dashboard', 'home', 'nyumbani', 'main screen', 'summary', 'muhtasari'],
            'help': ['help', 'guide', 'how to', 'msaada', 'mwongozo', 'saidia', 
                    'what can you do', 'uwezo wako', 'features'],
            'thanks': ['thank', 'thanks', 'asante', 'thank you', 'shukran', 'nice'],
            'inventory': ['inventory', 'stock', 'bidhaa', 'hisa', 'goods', 'product'],
            'time': ['time', 'date', 'saa', 'tarehe', 'today', 'leo', 'now', 'sasa hivi'],
            'search': ['search', 'tafuta', 'find', 'look for', 'transaction search'],
            'error': ['error', 'problem', 'issue', 'tatizo', 'shida', 'not working', 'haifanyi kazi']
        }
        
        self.responses = {
            'en': {
                'greeting': "Hello! 😊 I'm your LedgerMate assistant. How can I help you with your bookkeeping today?",
                
                'add_transaction': "📝 **To add a transaction:**\n\n" +
                    "1️⃣ Tap the **+ (plus) button** at the bottom of the screen\n" +
                    "2️⃣ Choose **Income** (money in) or **Expense** (money out)\n" +
                    "3️⃣ Enter the **amount** in KES\n" +
                    "4️⃣ Select a **category** (like Sales, Rent, etc.)\n" +
                    "5️⃣ Choose **payment method** (Cash/M-Pesa/Other)\n" +
                    "6️⃣ If M-Pesa, enter the **confirmation code**\n" +
                    "7️⃣ Add a **description** (optional but helpful)\n" +
                    "8️⃣ Tap **'Save Transaction'**\n\n" +
                    "💡 **Tip:** You can also edit or delete transactions by tapping on them in the list.",
                
                'view_report': "📊 **To view reports:**\n\n" +
                    "1️⃣ Tap **'Reports'** in the bottom menu\n" +
                    "2️⃣ Select the **period** you want:\n" +
                    "   • Daily - Today's transactions\n" +
                    "   • Weekly - Last 7 days\n" +
                    "   • Monthly - Last 30 days\n" +
                    "   • Custom - Choose your own dates\n" +
                    "3️⃣ Apply **filters** if needed (by type or category)\n" +
                    "4️⃣ Tap **'Generate Report'**\n" +
                    "5️⃣ View the chart and transaction list\n\n" +
                    "📥 **Export options:**\n" +
                    "• **PDF** - For printing or sharing\n" +
                    "• **CSV** - For Excel/spreadsheets\n" +
                    "• **Excel** - Direct Excel file\n" +
                    "• **Print** - Print directly",
                
                'mpesa': "📱 **Recording M-Pesa transactions:**\n\n" +
                    "1️⃣ When adding a transaction, select **'M-Pesa'** as payment method\n" +
                    "2️⃣ Enter the **M-Pesa confirmation code** (e.g., QW12RT34)\n" +
                    "3️⃣ This code helps you:\n" +
                    "   • Verify payments against your M-Pesa statement\n" +
                    "   • Search for specific transactions later\n" +
                    "   • Reconcile your records\n\n" +
                    "💡 **Note:** You can also record cash and other payment methods.\n\n" +
                    "🔍 To find an M-Pesa transaction later, use the search function and enter the code.",
                
                'category': "🏷️ **Managing Categories:**\n\n" +
                    "**Default Categories:**\n" +
                    "• **Income:** Sales, Services, M-Pesa Income\n" +
                    "• **Expense:** Inventory, Rent, Transport, Utilities, Salaries\n\n" +
                    "**To add custom categories:**\n" +
                    "1️⃣ Go to **Categories** from the profile menu\n" +
                    "2️⃣ Tap **'Add Category'**\n" +
                    "3️⃣ Enter category name\n" +
                    "4️⃣ Choose type (Income/Expense)\n" +
                    "5️⃣ Select an icon and color\n" +
                    "6️⃣ Tap **'Save'**\n\n" +
                    "📊 Categories help you understand where your money comes from and goes!",
                
                'delete': "🗑️ **To delete a transaction:**\n\n" +
                    "1️⃣ Find the transaction in the **Transactions list**\n" +
                    "2️⃣ **Tap on it** to open details\n" +
                    "3️⃣ Tap the **red 'Delete' button**\n" +
                    "4️⃣ **Confirm** when asked\n\n" +
                    "⚠️ **Important:**\n" +
                    "• Deleted transactions are hidden but not permanently removed\n" +
                    "• You can recover them if needed (contact support)\n" +
                    "• Consider editing instead of deleting if you made a small mistake",
                
                'export': "📤 **Exporting your data:**\n\n" +
                    "1️⃣ Go to **Reports**\n" +
                    "2️⃣ Generate your report with desired filters\n" +
                    "3️⃣ Look for the **export buttons** at the top\n" +
                    "4️⃣ Choose your format:\n\n" +
                    "   **PDF** 📄 - Best for:\n" +
                    "   • Sharing with others\n" +
                    "   • Printing records\n" +
                    "   • Keeping as proof\n\n" +
                    "   **CSV** 📊 - Best for:\n" +
                    "   • Opening in Excel\n" +
                    "   • Data analysis\n" +
                    "   • Importing to other systems\n\n" +
                    "   **Excel** 📈 - Best for:\n" +
                    "   • Advanced calculations\n" +
                    "   • Creating charts\n" +
                    "   • Professional reports\n\n" +
                    "5️⃣ File will **download automatically**",
                
                'balance': "💰 **Understanding your balance:**\n\n" +
                    "Your **Net Balance** = Total Income - Total Expenses\n\n" +
                    "**On Dashboard:**\n" +
                    "• 📈 **Green cards** show Income\n" +
                    "• 📉 **Red cards** show Expenses\n" +
                    "• 💜 **Purple card** shows Net Balance\n\n" +
                    "**If Net Balance is:**\n" +
                    "• **Positive (+)** → Your business is profitable\n" +
                    "• **Negative (-)** → You're spending more than earning\n" +
                    "• **Zero (0)** → You broke even\n\n" +
                    "📊 Check the chart to see trends over time!",
                
                'dashboard': "🏠 **Using the Dashboard:**\n\n" +
                    "Your dashboard shows you at a glance:\n\n" +
                    "**Top Cards:**\n" +
                    "• **Total Income** - All money received\n" +
                    "• **Total Expense** - All money spent\n" +
                    "• **Net Balance** - Your profit/loss\n\n" +
                    "**Chart:**\n" +
                    "• Shows daily income vs expense for last 30 days\n" +
                    "• Green bars = Income\n" +
                    "• Red bars = Expense\n\n" +
                    "**Recent Transactions:**\n" +
                    "• Last 10 transactions\n" +
                    "• Tap any to see details\n" +
                    "• 'View All' to see full list",
                
                'help': "🤖 **I can help you with:**\n\n" +
                    "📝 **Transactions** - Adding, editing, deleting\n" +
                    "📊 **Reports** - Generating and exporting\n" +
                    "📱 **M-Pesa** - Recording mobile money\n" +
                    "🏷️ **Categories** - Organizing your entries\n" +
                    "💰 **Balance** - Understanding your finances\n" +
                    "📤 **Export** - Saving your data\n" +
                    "🏠 **Dashboard** - Using the main screen\n\n" +
                    "**Just ask me a question like:**\n" +
                    "• 'How do I add a transaction?'\n" +
                    "• 'Show me how to export reports'\n" +
                    "• 'What are categories for?'\n" +
                    "• 'How to record M-Pesa?'\n\n" +
                    "Type your question and I'll help! 😊",
                
                'thanks': "You're welcome! 😊 Happy bookkeeping! Feel free to ask if you need anything else.",
                
                'inventory': "📦 **Inventory Management:**\n\n" +
                    "LedgerMate helps track inventory-related expenses:\n\n" +
                    "**To record inventory purchases:**\n" +
                    "1️⃣ Add an **Expense** transaction\n" +
                    "2️⃣ Select **'Inventory'** category\n" +
                    "3️⃣ Enter amount spent on stock\n" +
                    "4️⃣ Add description (e.g., 'Bought 10 boxes of goods')\n\n" +
                    "**To track inventory sales:**\n" +
                    "1️⃣ Add an **Income** transaction\n" +
                    "2️⃣ Select **'Sales'** category\n" +
                    "3️⃣ Enter amount received\n" +
                    "4️⃣ Describe what was sold\n\n" +
                    "💡 This helps you see:\n" +
                    "• How much you spend on stock\n" +
                    "• Sales revenue\n" +
                    "• Profit margins on products",
                
                'time': "⏰ **Current Information:**\n\n" +
                    f"• Today's date: **{datetime.now().strftime('%B %d, %Y')}**\n" +
                    f"• Current time: **{datetime.now().strftime('%I:%M %p')}**\n\n" +
                    "You can:\n" +
                    "• View today's transactions on Dashboard\n" +
                    "• Generate daily reports\n" +
                    "• Filter transactions by date",
                
                'search': "🔍 **Searching Transactions:**\n\n" +
                    "To find specific transactions:\n\n" +
                    "1️⃣ Go to **Transactions** page\n" +
                    "2️⃣ Use the **search bar** at the top\n" +
                    "3️⃣ Search by:\n" +
                    "   • Description\n" +
                    "   • Amount\n" +
                    "   • M-Pesa code\n" +
                    "   • Category\n\n" +
                    "**Filters you can use:**\n" +
                    "• Date range\n" +
                    "• Transaction type\n" +
                    "• Payment method\n" +
                    "• Category\n\n" +
                    "Results update as you type!",
                
                'error': "🛠️ **Having trouble? Here are common fixes:**\n\n" +
                    "**Can't add transaction?**\n" +
                    "• Make sure all required fields are filled\n" +
                    "• Amount must be greater than 0\n" +
                    "• Check your internet connection\n\n" +
                    "**Reports not loading?**\n" +
                    "• Try refreshing the page\n" +
                    "• Select a smaller date range\n" +
                    "• Check if you have transactions\n\n" +
                    "**App not responding?**\n" +
                    "• Refresh the page\n" +
                    "• Clear browser cache\n" +
                    "• Log out and log back in\n\n" +
                    "Still having issues? Contact support at support@ledgermate.co.ke",
                
                'default': "I'm not sure I understand. Could you please rephrase?\n\n" +
                    "You can ask me about:\n" +
                    "• 📝 Adding transactions\n" +
                    "• 📊 Viewing reports\n" +
                    "• 📱 M-Pesa recording\n" +
                    "• 🏷️ Categories\n" +
                    "• 📤 Exporting data\n" +
                    "• 💰 Balance\n" +
                    "• 🏠 Dashboard\n\n" +
                    "Or type 'help' to see everything I can do!"
            },
            'sw': {
                'greeting': "Habari! 😊 Mimi ni msaidizi wako wa LedgerMate. Nikusaidie vipi na uhasibu wako leo?",
                
                'add_transaction': "📝 **Kuongeza muamala:**\n\n" +
                    "1️⃣ Bonyeza kitufe cha **+ (plus)** chini ya skrini\n" +
                    "2️⃣ Chagua **Mapato** (pesa inayoingia) au **Matumizi** (pesa inayotoka)\n" +
                    "3️⃣ Weka **kiasi** kwa KES\n" +
                    "4️⃣ Chagua **aina** (kama Mauzo, Kodi, nk.)\n" +
                    "5️⃣ Chagua **njia ya malipo** (Taslimu/M-Pesa/Nyingine)\n" +
                    "6️⃣ Ikiwa ni M-Pesa, weka **nambari ya uthibitisho**\n" +
                    "7️⃣ Ongeza **maelezo** (si lazima lakini inasaidia)\n" +
                    "8️⃣ Bonyeza **'Hifadhi Muamala'**\n\n" +
                    "💡 **Kidokezo:** Unaweza kuhariri au kufuta miamala kwa kubonyeza kwenye orodha.",
                
                'view_report': "📊 **Kutazama ripoti:**\n\n" +
                    "1️⃣ Bonyeza **'Ripoti'** kwenye menyu ya chini\n" +
                    "2️⃣ Chagua **kipindi** unachotaka:\n" +
                    "   • Kila Siku - Miamala ya leo\n" +
                    "   • Kila Wiki - Siku 7 zilizopita\n" +
                    "   • Kila Mwezi - Siku 30 zilizopita\n" +
                    "   • Maalum - Chagua tarehe zako\n" +
                    "3️⃣ Weka **vichujio** ikihitajika\n" +
                    "4️⃣ Bonyeza **'Tengeneza Ripoti'**\n" +
                    "5️⃣ Tazama chati na orodha ya miamala\n\n" +
                    "📥 **Njia za kuhamisha:**\n" +
                    "• **PDF** - Kuchapisha au kushiriki\n" +
                    "• **CSV** - Kwa Excel/spreadsheet\n" +
                    "• **Excel** - Faili ya Excel moja kwa moja\n" +
                    "• **Chapisha** - Chapisha moja kwa moja",
                
                'mpesa': "📱 **Kurekodi miamala ya M-Pesa:**\n\n" +
                    "1️⃣ Unapoongeza muamala, chagua **'M-Pesa'** kama njia ya malipo\n" +
                    "2️⃣ Weka **nambari ya uthibitisho ya M-Pesa**\n" +
                    "3️⃣ Nambari hii inakusaidia:\n" +
                    "   • Kuthibitisha malipo dhidi ya taarifa yako ya M-Pesa\n" +
                    "   • Kutafuta miamala mahususi baadaye\n" +
                    "   • Kulinganisha rekodi zako\n\n" +
                    "💡 **Kumbuka:** Unaweza pia kurekodi taslimu na njia nyingine za malipo.",
                
                'category': "🏷️ **Kudhibiti Aina:**\n\n" +
                    "**Aina za Msingi:**\n" +
                    "• **Mapato:** Mauzo, Huduma, Mapato ya M-Pesa\n" +
                    "• **Matumizi:** Bidhaa, Kodi, Usafiri, Huduma, Mishahara\n\n" +
                    "**Kuongeza aina mpya:**\n" +
                    "1️⃣ Nenda kwenye **Aina** kutoka kwenye menyu\n" +
                    "2️⃣ Bonyeza **'Ongeza Aina'**\n" +
                    "3️⃣ Weka jina la aina\n" +
                    "4️⃣ Chagua aina (Mapato/Matumizi)\n" +
                    "5️⃣ Chagua ikoni na rangi\n" +
                    "6️⃣ Bonyeza **'Hifadhi'**",
                
                'delete': "🗑️ **Kufuta muamala:**\n\n" +
                    "1️⃣ Tafuta muamala kwenye orodha ya **Miamala**\n" +
                    "2️⃣ **Bonyeza juu yake** kufungua maelezo\n" +
                    "3️⃣ Bonyeza kitufe **chekundu cha 'Futa'**\n" +
                    "4️⃣ **Thibitisha** ukiulizwa\n\n" +
                    "⚠️ **Muhimu:** Unaweza kupata tena muamala ukihitaji",
                
                'export': "📤 **Kuhamisha data yako:**\n\n" +
                    "1️⃣ Nenda kwenye **Ripoti**\n" +
                    "2️⃣ Tengeneza ripoti yako\n" +
                    "3️⃣ Chagua muundo:\n" +
                    "   • **PDF** - Kushiriki au kuchapisha\n" +
                    "   • **CSV** - Kufungua kwa Excel\n" +
                    "   • **Excel** - Faili ya Excel moja kwa moja\n" +
                    "4️⃣ Faili itapakuliwa moja kwa moja",
                
                'balance': "💰 **Kuelewa usawa wako:**\n\n" +
                    "**Usawa Halisi** = Jumla ya Mapato - Jumla ya Matumizi\n\n" +
                    "**Kwenye Dashibodi:**\n" +
                    "• 📈 **Kadi za kijani** zinaonyesha Mapato\n" +
                    "• 📉 **Kadi nyekundu** zinaonyesha Matumizi\n" +
                    "• 💜 **Kadi ya zambarau** inaonyesha Usawa Halisi",
                
                'dashboard': "🏠 **Kutumia Dashibodi:**\n\n" +
                    "Dashibodi yako inaonyesha:\n\n" +
                    "**Kadi za Juu:**\n" +
                    "• **Jumla ya Mapato** - Pesa zote zilizoingia\n" +
                    "• **Jumla ya Matumizi** - Pesa zote zilizotoka\n" +
                    "• **Usawa Halisi** - Faida/hasara yako",
                
                'help': "🤖 **Naweza kukusaidia kwa:**\n\n" +
                    "📝 **Miamala** - Kuongeza, kuhariri, kufuta\n" +
                    "📊 **Ripoti** - Kutengeneza na kuhamisha\n" +
                    "📱 **M-Pesa** - Kurekodi pesa za simu\n" +
                    "🏷️ **Aina** - Kupanga miamala yako\n" +
                    "💰 **Usawa** - Kuelewa fedha zako\n" +
                    "📤 **Kuhamisha** - Kuhifadhi data yako\n\n" +
                    "**Niulize swali kama:**\n" +
                    "• 'Jinsi ya kuongeza muamala?'\n" +
                    "• 'Nionyeshe jinsi ya kuhamisha ripoti'\n" +
                    "• 'Aina za matumizi ni zipi?'\n" +
                    "• 'Jinsi ya kurekodi M-Pesa?'",
                
                'thanks': "Karibu! 😊 Uhasibu mwema! Uliza ukihitaji msaada zaidi.",
                
                'inventory': "📦 **Usimamizi wa Bidhaa:**\n\n" +
                    "Kurekodi ununuzi wa bidhaa:\n" +
                    "1️⃣ Ongeza muamala wa **Matumizi**\n" +
                    "2️⃣ Chagua aina ya **'Bidhaa'**\n" +
                    "3️⃣ Weka kiasi kilichotumika\n" +
                    "4️⃣ Ongeza maelezo",
                
                'time': "⏰ **Taarifa za Sasa:**\n\n" +
                    f"• Tarehe ya leo: **{datetime.now().strftime('%d %B, %Y')}**\n" +
                    f"• Sasa ni saa: **{datetime.now().strftime('%I:%M %p')}**",
                
                'search': "🔍 **Kutafuta Miamala:**\n\n" +
                    "1️⃣ Nenda kwenye ukurasa wa **Miamala**\n" +
                    "2️⃣ Tumia **upau wa kutafutia**\n" +
                    "3️⃣ Tafuta kwa:\n" +
                    "   • Maelezo\n" +
                    "   • Kiasi\n" +
                    "   • Nambari ya M-Pesa\n" +
                    "   • Aina",
                
                'error': "🛠️ **Shida? Hapa ni masuluhisho:**\n\n" +
                    "**Huwezi kuongeza muamala?**\n" +
                    "• Hakikisha sehemu zote zimejazwa\n" +
                    "• Kiasi lazima kiwe zaidi ya 0\n" +
                    "• Angalia muunganisho wako wa intaneti\n\n" +
                    "Bado una shida? Wasiliana nasi: support@ledgermate.co.ke",
                
                'default': "Samahani, sielewi. Tafadhali uliza tena?\n\n" +
                    "Unaweza kuniuliza kuhusu:\n" +
                    "• 📝 Kuongeza miamala\n" +
                    "• 📊 Kutazama ripoti\n" +
                    "• 📱 Kurekodi M-Pesa\n" +
                    "• 🏷️ Aina\n" +
                    "• 📤 Kuhamisha data\n" +
                    "• 💰 Usawa\n\n" +
                    "Au andika 'msaada' kuona yote ninaweza kufanya!"
            }
        }
    
    def get_response(self, message, language='en'):
        """Get chatbot response based on user message"""
        if not message:
            return self.responses[language]['default']
        
        # Convert to lowercase for matching
        message_lower = message.lower().strip()
        
        # Check for time/date queries
        if any(word in message_lower for word in ['time', 'date', 'today', 'saa', 'tarehe', 'leo']):
            return self._get_time_response(language)
        
        # Check each intent
        for intent, keywords in self.intents.items():
            if any(keyword in message_lower for keyword in keywords):
                return self.responses[language].get(intent, self.responses[language]['default'])
        
        # Check for questions about specific features
        if 'how' in message_lower or 'jinsi' in message_lower:
            if 'add' in message_lower or 'ongeza' in message_lower:
                return self.responses[language]['add_transaction']
            elif 'report' in message_lower or 'ripoti' in message_lower:
                return self.responses[language]['view_report']
            elif 'mpesa' in message_lower:
                return self.responses[language]['mpesa']
            elif 'categor' in message_lower or 'aina' in message_lower:
                return self.responses[language]['category']
            elif 'export' in message_lower or 'hamisha' in message_lower:
                return self.responses[language]['export']
        
        # Default response
        return self.responses[language]['default']
    
    def _get_time_response(self, language='en'):
        """Get time and date response"""
        now = datetime.now()
        
        if language == 'en':
            return (f"⏰ **Current Information:**\n\n"
                   f"• Today's date: **{now.strftime('%B %d, %Y')}**\n"
                   f"• Current time: **{now.strftime('%I:%M %p')}**\n\n"
                   f"• Day of week: **{now.strftime('%A')}**\n"
                   f"• Week of year: **{now.strftime('%W')}**\n\n"
                   f"What would you like to do with this information?")
        else:
            return (f"⏰ **Taarifa za Sasa:**\n\n"
                   f"• Tarehe ya leo: **{now.strftime('%d %B, %Y')}**\n"
                   f"• Sasa ni saa: **{now.strftime('%I:%M %p')}**\n\n"
                   f"• Siku ya wiki: **{self._get_swahili_day(now.strftime('%A'))}**\n\n"
                   f"Ungependa kufanya nini na taarifa hii?")
    
    def _get_swahili_day(self, english_day):
        """Convert English day to Swahili"""
        days = {
            'Monday': 'Jumatatu',
            'Tuesday': 'Jumanne',
            'Wednesday': 'Jumatano',
            'Thursday': 'Alhamisi',
            'Friday': 'Ijumaa',
            'Saturday': 'Jumamosi',
            'Sunday': 'Jumapili'
        }
        return days.get(english_day, english_day)
    
    def get_contextual_help(self, page, language='en'):
        """Get help specific to the current page"""
        contextual_help = {
            'en': {
                'dashboard': "💡 **On Dashboard:**\n• View your total income, expenses, and net balance\n• Check the chart to see trends\n• See your 10 most recent transactions\n• Tap any transaction for details",
                
                'transactions': "💡 **On Transactions Page:**\n• View all your transactions\n• Use search to find specific ones\n• Filter by date, type, or category\n• Tap any transaction to edit or delete",
                
                'add_transaction': "💡 **Adding a Transaction:**\n• Choose income or expense\n• Enter amount in KES\n• Select appropriate category\n• For M-Pesa, include confirmation code\n• Add description for clarity",
                
                'reports': "💡 **On Reports Page:**\n• Generate reports for any period\n• Filter by type and category\n• View charts and tables\n• Export as PDF, CSV, or Excel",
                
                'categories': "💡 **Managing Categories:**\n• Default categories are provided\n• Add custom categories as needed\n• Each category has an icon and color\n• Organize income and expense separately"
            },
            'sw': {
                'dashboard': "💡 **Kwenye Dashibodi:**\n• Angalia mapato, matumizi na usawa wako\n• Angalia chati kuona mwenendo\n• Angalia miamala 10 ya karibuni\n• Bonyeza muamala kuona maelezo",
                
                'transactions': "💡 **Kwenye Miamala:**\n• Angalia miamala yako yote\n• Tumia utafutaji kupata maalum\n• Chuja kwa tarehe, aina\n• Bonyeza muamala kuhariri au kufuta",
                
                'add_transaction': "💡 **Kuongeza Muamala:**\n• Chagua mapato au matumizi\n• Weka kiasi kwa KES\n• Chagua aina sahihi\n• Kwa M-Pesa, weka nambari ya uthibitisho\n• Ongeza maelezo kwa uwazi",
                
                'reports': "💡 **Kwenye Ripoti:**\n• Tengeneza ripoti za kipindi chochote\n• Chuja kwa aina\n• Angalia chati na majedwali\n• Hamisha kama PDF, CSV, au Excel",
                
                'categories': "💡 **Kudhibiti Aina:**\n• Aina za msingi zinatolewa\n• Ongeza aina zako mwenyewe\n• Kila aina ina ikoni na rangi\n• Panga mapato na matumizi tofauti"
            }
        }
        
        return contextual_help.get(language, {}).get(page, "")
    
    def get_financial_advice(self, transactions_data, language='en'):
        """Provide simple financial advice based on transactions"""
        if not transactions_data:
            if language == 'en':
                return "Start adding transactions to get personalized financial insights!"
            else:
                return "Anza kuongeza miamala kupata ushauri wa kifedha!"
        
        try:
            income = transactions_data.get('total_income', 0)
            expense = transactions_data.get('total_expense', 0)
            net = income - expense
            
            if language == 'en':
                advice = "📊 **Financial Insight:**\n\n"
                
                if net > 0:
                    advice += f"✅ **Good news!** Your business is profitable with a net of KES {net:,.2f}\n\n"
                    advice += "💡 **Suggestions:**\n"
                    advice += "• Consider reinvesting some profits\n"
                    advice += "• Build an emergency fund\n"
                    advice += "• Look for opportunities to expand"
                elif net < 0:
                    advice += f"⚠️ **Notice:** Your expenses (KES {expense:,.2f}) exceed income (KES {income:,.2f})\n\n"
                    advice += "💡 **Suggestions:**\n"
                    advice += "• Review your expense categories\n"
                    advice+= "• Identify areas to cut costs\n"
                    advice+= "• Look for ways to increase sales"
                else:
                    advice += f"You're breaking even (Income: KES {income:,.2f}, Expenses: KES {expense:,.2f})\n\n"
                    advice += "💡 **Suggestions:**\n"
                    advice += "• Focus on increasing income\n"
                    advice += "• Look for small ways to reduce costs\n"
                    advice += "• Even small profits add up over time"
                
                return advice
            else:
                advice = "📊 **Ushauri wa Kifedha:**\n\n"
                
                if net > 0:
                    advice += f"✅ **Habari njema!** Biashara yako ina faida ya KES {net:,.2f}\n\n"
                    advice += "💡 **Mapendekezo:**\n"
                    advice += "• Fikiria kuwekeza tena baadhi ya faida\n"
                    advice += "• Jenga akiba ya dharura\n"
                    advice += "• Tafuta fursa za kupanua"
                elif net < 0:
                    advice += f"⚠️ **Ilani:** Matumizi yako (KES {expense:,.2f}) yanazidi mapato (KES {income:,.2f})\n\n"
                    advice += "💡 **Mapendekezo:**\n"
                    advice += "• Pitia aina zako za matumizi\n"
                    advice += "• Tambua maeneo ya kupunguza gharama\n"
                    advice += "• Tafuta njia za kuongeza mauzo"
                else:
                    advice += f"Unavunja sawa (Mapato: KES {income:,.2f}, Matumizi: KES {expense:,.2f})\n\n"
                    advice += "💡 **Mapendekezo:**\n"
                    advice += "• Zingatia kuongeza mapato\n"
                    advice += "• Tafuta njia ndogo za kupunguza gharama\n"
                    advice += "• Hata faida ndogo hujumlishka kwa muda"
                
                return advice
                
        except Exception as e:
            if language == 'en':
                return "I can't provide advice right now. Keep adding transactions!"
            else:
                return "Siwezi kutoa ushauri sasa hivi. Endelea kuongeza miamala!"
    
    def get_quick_replies(self, language='en'):
        """Get quick reply suggestions for the chatbot"""
        if language == 'en':
            return [
                "How to add transaction?",
                "View my reports",
                "Record M-Pesa",
                "What are categories?",
                "Export data",
                "Help me understand balance",
                "Financial advice",
                "What time is it?"
            ]
        else:
            return [
                "Jinsi ya kuongeza muamala?",
                "Tazama ripoti zangu",
                "Rekodi M-Pesa",
                "Aina ni nini?",
                "Hamisha data",
                "Nisaidie kuelewa usawa",
                "Ushauri wa kifedha",
                "Saa ngapi sasa?"
            ]
    
    def detect_sentiment(self, message):
        """Simple sentiment detection for better responses"""
        message_lower = message.lower()
        
        positive_words = ['good', 'great', 'awesome', 'nice', 'love', 'happy', 'asante', 'sawa', 'poa']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'sad', 'problem', 'shida', 'tatizo']
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def handle_follow_up(self, message, conversation_history, language='en'):
        """Handle follow-up questions based on conversation context"""
        message_lower = message.lower()
        
        # Check if user is asking for more details about previous topic
        if any(word in message_lower for word in ['more', 'zaidi', 'detail', 'maelezo']):
            if conversation_history and len(conversation_history) > 0:
                last_topic = conversation_history[-1].get('intent', '')
                if last_topic:
                    return self.responses[language].get(last_topic + '_detailed', 
                                                        "I can provide more details. What specifically would you like to know?")
        
        # Check if user is confirming something
        if any(word in message_lower for word in ['yes', 'ndiyo', 'sawa', 'okay']):
            return "Great! What else would you like help with?"
        
        # Check if user is saying no
        if any(word in message_lower for word in ['no', 'hapana', 'sivyo']):
            return "No problem! Feel free to ask if you need anything else."
        
        return None


# Create singleton instance
chatbot_service = ChatbotService()