from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.menu import MainMenuKeyboard
from app.keyboards.admin import AdminKeyboard
from app.services.leaderboard_service import LeaderboardService
from app.db.base import get_db
from app.repositories.leaderboard_repo import LeaderboardRepository
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.user_repo import UserRepository
from app.utils.constants import EMOJIS
from app.utils.helpers import format_number
from app.utils.safe_edit import edit_text_safe

router = Router()

class LeaderboardStates(StatesGroup):
    viewing_leaderboard = State()

@router.message(Command("leaderboard"))
async def command_leaderboard(message: types.Message):
    """Handle /leaderboard command - show leaderboard options"""
    await message.answer(
        "🏆 *Leaderboards*\n\n"
        "Compete with other students and track your ranking!\n\n"
        "Choose a leaderboard period:",
        parse_mode='Markdown',
        reply_markup=MainMenuKeyboard.get_leaderboard_keyboard()
    )

@router.callback_query(F.data.startswith("leaderboard_"))
async def show_leaderboard(callback: types.CallbackQuery):
    """Show specific leaderboard"""
    period = callback.data.split("_")[1]  # daily, weekly, monthly, overall
    user_id = callback.from_user.id  # Get current user's ID
    
    period_names = {
        'daily': 'Daily',
        'weekly': 'Weekly',
        'monthly': 'Monthly',
        'overall': 'All-Time'
    }
    
    period_name = period_names.get(period, period.capitalize())
    
    async for session in get_db():
        leaderboard_repo = LeaderboardRepository(session)
        attempt_repo = AttemptRepository(session)
        
        leaderboard_service = LeaderboardService(leaderboard_repo, attempt_repo)
        
        try:
            # Get leaderboard data with real-time calculation
            leaderboard_data = await leaderboard_service.get_leaderboard(period, limit=20, user_id=user_id)
            leaderboard = leaderboard_data.get('leaderboard', [])
            total_users = leaderboard_data.get('total_users', 0)
            user_rank = leaderboard_data.get('user_rank')
            
            # Prepare leaderboard message
            leaderboard_msg = (
                f"🏆 *{period_name} Leaderboard*\n\n"
                f"Total participants: {total_users}\n"
                f"Updated: {EMOJIS['time']} Recently\n\n"
            )
            
            if not leaderboard:
                leaderboard_msg += (
                    "No rankings available yet.\n"
                    "Be the first to complete a quiz!\n\n"
                    "Start a quiz now to get on the leaderboard! 🚀"
                )
            else:
                # Show top 10
                leaderboard_msg += "🏅 *Top Performers:*\n\n"
                
                medals = {1: "🥇", 2: "🥈", 3: "🥉"}
                for entry in leaderboard[:10]:
                    medal = medals.get(entry['rank'], f"{entry['rank']}.")
                    username = entry.get('username', f"User {entry.get('user_id', '')}")
                    
                    # Truncate long usernames
                    if len(username) > 15:
                        username = username[:12] + "..."
                    
                    leaderboard_msg += (
                        f"{medal} *{username}*\n"
                        f"   📊 {entry.get('score', 0)} pts | "
                        f"🔢 {entry.get('questions', 0)} q\n\n"
                    )
            
            # Add user's own rank if available
            if user_rank:
                leaderboard_msg += (
                    f"\n📊 *Your Position:*\n"
                    f"• Rank: #{user_rank.get('rank', 'N/A')}\n"
                    f"• Score: {user_rank.get('score', 0)} pts\n"
                    f"• Questions: {user_rank.get('questions', 0)}\n"
                )
            
            leaderboard_msg += "\n💡 *How rankings work:*\n"
            leaderboard_msg += "• Points: Simple=1, Medium=2, Hard=3 per correct answer\n"
            leaderboard_msg += "• Minimum 5 questions required to qualify\n"
            leaderboard_msg += "• Updated in real-time\n"
            
            await edit_text_safe(
                callback,
                leaderboard_msg,
                reply_markup=MainMenuKeyboard.get_leaderboard_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await edit_text_safe(
                callback,
                f"❌ Error loading leaderboard: {str(e)}\n"
                "Please try again later.",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()

@router.callback_query(F.data == "my_leaderboard_stats")
async def my_leaderboard_stats(callback: types.CallbackQuery):
    """Show user's leaderboard statistics across all periods"""
    user_id = callback.from_user.id
    
    async for session in get_db():
        leaderboard_repo = LeaderboardRepository(session)
        attempt_repo = AttemptRepository(session)
        
        leaderboard_service = LeaderboardService(leaderboard_repo, attempt_repo)
        
        try:
            # Get user's leaderboard summary
            summary = await leaderboard_service.get_user_leaderboard_summary(user_id)
            
            stats_msg = (
                f"📊 *Your Leaderboard Statistics*\n\n"
                f"👤 *User:* {callback.from_user.first_name or 'Student'}\n\n"
            )
            
            # Show rankings for each period
            period_display = {
                'daily': '📅 Daily',
                'weekly': '📊 Weekly',
                'monthly': '📈 Monthly',
                'overall': '🏆 All-Time'
            }
            
            has_any_ranking = False
            
            for period, data in summary.get('summary', {}).items():
                period_name = period_display.get(period, period.capitalize())
                
                if data:
                    has_any_ranking = True
                    stats_msg += (
                        f"{period_name}:\n"
                        f"• Rank: #{data.get('rank', 'N/A')}\n"
                        f"• Score: {data.get('score', 0)} pts\n"
                        f"• Questions: {data.get('questions', 0)}\n\n"
                    )
                else:
                    stats_msg += f"{period_name}: Not ranked yet\n\n"
            
            # Show best rank
            best_rank = summary.get('best_rank')
            best_period = summary.get('best_period')
            
            if best_rank:
                best_period_name = period_display.get(best_period, best_period.capitalize())
                stats_msg += (
                    f"⭐ *Best Achievement:*\n"
                    f"• Best rank: #{best_rank} ({best_period_name})\n\n"
                )
            
            if not has_any_ranking:
                stats_msg += (
                    "🎯 *Get Started:*\n"
                    "Complete your first quiz to appear on the leaderboard!\n"
                    "Aim for accuracy to climb the rankings faster.\n\n"
                )
            
            stats_msg += (
                "💪 *Tips to improve ranking:*\n"
                "1. Answer questions accurately\n"
                "2. Try higher difficulty levels (more points)\n"
                "3. Practice consistently\n"
                "4. Review explanations for wrong answers\n"
            )
            
            await edit_text_safe(
                callback,
                stats_msg,
                reply_markup=MainMenuKeyboard.get_leaderboard_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await edit_text_safe(
                callback,
                f"❌ Error loading statistics: {str(e)}",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()

@router.callback_query(F.data == "top_performers")
async def top_performers_callback(callback: types.CallbackQuery):
    """Show top performers across all periods"""
    async for session in get_db():
        leaderboard_repo = LeaderboardRepository(session)
        attempt_repo = AttemptRepository(session)
        
        leaderboard_service = LeaderboardService(leaderboard_repo, attempt_repo)
        
        try:
            # Get top performers using real-time calculation
            leaderboard_data = await leaderboard_service.get_leaderboard('overall', limit=5)
            top_performers = leaderboard_data.get('leaderboard', [])
            
            if not top_performers:
                top_msg = (
                    f"🌟 *Top Performers*\n\n"
                    f"No top performers identified yet.\n"
                    f"Be the first to claim the top spot!\n\n"
                    f"Start practicing now to become a top performer! 🚀"
                )
            else:
                top_msg = (
                    f"🌟 *All-Time Top Performers*\n\n"
                    f"These students have excelled across all leaderboards:\n\n"
                )
                
                medals = {1: "🥇", 2: "🥈", 3: "🥉"}
                for i, performer in enumerate(top_performers, 1):
                    medal = medals.get(i, f"{i}.")
                    username = performer.get('username', f"User {performer.get('user_id', '')}")
                    
                    # Truncate long usernames
                    if len(username) > 15:
                        username = username[:12] + "..."
                    
                    top_msg += (
                        f"{medal} *{username}*\n"
                        f"   📊 Total Score: {format_number(performer.get('score', 0))}\n"
                        f"   🔢 Questions: {performer.get('questions', 0)}\n\n"
                    )
            
            top_msg += (
                "🏆 *Hall of Fame Criteria:*\n"
                "• Consistent performance across periods\n"
                "• High accuracy in difficult questions\n"
                "• Active participation\n"
            )
            
            await edit_text_safe(
                callback,
                top_msg,
                reply_markup=MainMenuKeyboard.get_leaderboard_keyboard(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await edit_text_safe(
                callback,
                f"❌ Error loading top performers: {str(e)}",
                reply_markup=MainMenuKeyboard.get_main_menu_inline()
            )
    
    await callback.answer()

@router.callback_query(F.data == "leaderboard_rules")
async def leaderboard_rules_callback(callback: types.CallbackQuery):
    """Show leaderboard rules and scoring system"""
    rules_msg = (
        f"📜 *Leaderboard Rules & Scoring*\n\n"
        
        f"🏆 *Scoring System:*\n"
        f"• Correct answer - Simple: 1 point\n"
        f"• Correct answer - Medium: 2 points\n"
        f"• Correct answer - Hard: 3 points\n"
        f"• Wrong answer: 0 points\n\n"
        
        f"📊 *Ranking Criteria:*\n"
        f"1. Total points (primary)\n"
        f"2. Number of questions (secondary)\n"
        f"3. Recent activity (tertiary)\n\n"
        
        f"🎯 *Qualification Requirements:*\n"
        f"• Minimum 5 questions attempted\n"
        f"• At least 1 quiz completed\n"
        f"• Active account (not blocked)\n\n"
        
        f"⏰ *Leaderboard Periods:*\n"
        f"• 📅 Daily: Today's quiz activity\n"
        f"• 📊 Weekly: Current week's activity\n"
        f"• 📈 Monthly: Current month's activity\n"
        f"• 🏆 All-Time: Cumulative (never resets)\n\n"
        
        f"⚠️ *Important Notes:*\n"
        f"• Cheating or automated answers will result in ban\n"
        f"• Leaderboards update in real-time\n"
        f"• Your best rank across periods is tracked\n\n"
        
        f"💡 *Tips for Climbing Leaderboards:*\n"
        f"1. Focus on accuracy over speed\n"
        f"2. Challenge yourself with higher difficulties\n"
        f"3. Practice consistently daily\n"
        f"4. Review explanations to learn from mistakes\n"
    )
    
    await edit_text_safe(
        callback,
        rules_msg,
        reply_markup=MainMenuKeyboard.get_leaderboard_keyboard(),
        parse_mode='Markdown'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_user_profile_"))
async def view_user_profile_leaderboard(callback: types.CallbackQuery):
    """View another user's profile from leaderboard"""
    # Parse: view_user_profile_userId
    parts = callback.data.split("_")
    if len(parts) != 4:
        await callback.answer("Invalid request", show_alert=True)
        return
    
    user_id = int(parts[3])
    
    # In a complete implementation, fetch and display user's public profile
    # This would show their ranking history, achievements, etc.
    
    await callback.answer(
        "User profile viewing feature coming soon!",
        show_alert=True
    )

@router.callback_query(F.data == "compare_with_friends")
async def compare_with_friends_callback(callback: types.CallbackQuery):
    """Compare progress with friends (placeholder)"""
    await callback.answer(
        "Friend comparison feature coming soon!\n"
        "You'll be able to compare progress with other students.",
        show_alert=True
    )

@router.callback_query(F.data == "achievements")
async def achievements_callback(callback: types.CallbackQuery):
    """Show user's achievements and badges"""
    # In a complete implementation, this would show:
    # - Badges earned (First Quiz, Accuracy Master, etc.)
    # - Milestones reached
    # - Streaks and consistency awards
    
    achievements_msg = (
        f"🎖️ *Achievements & Badges*\n\n"
        f"🌟 *Your Achievements:*\n"
        f"• 🥇 First Quiz Completed\n"
        f"• 📚 10 Quizzes Mastered\n"
        f"• ⚡ Quick Learner (80%+ accuracy)\n"
        f"• 🏆 Weekly Top 10\n\n"
        
        f"🎯 *In Progress:*\n"
        f"• 📊 50 Questions (45/50)\n"
        f"• 💪 7-Day Streak (3/7)\n"
        f"• 🧠 Master All Subjects (2/5)\n\n"
        
        f"🏅 *Available Badges:*\n"
        f"• 🥇 Quiz Champion (Top 3 overall)\n"
        f"• 📈 Accuracy King (95%+ accuracy)\n"
        f"• ⏰ Speed Demon (Fast answers)\n"
        f"• 🎯 Perfect Score (100% on hard quiz)\n\n"
        
        f"Keep practicing to unlock more achievements! 💪"
    )
    
    await edit_text_safe(
        callback,
        achievements_msg,
        reply_markup=MainMenuKeyboard.get_leaderboard_keyboard(),
        parse_mode='Markdown'
    )
    await callback.answer()

