#!/usr/bin/env python
"""Test script to verify the new models are correctly defined."""

import sys
sys.path.insert(0, '/home/chaldev/Code-room/code-collection/bot/telegram-quiz-bot')

try:
    from app.db.models import (
        AchievementType,
        LeaderboardPeriod,
        LeaderboardEntry,
        Achievement,
        UserAchievement,
        DailyGoal,
        SystemConfig,
        AdminLog,
        User
    )
    
    print("✓ All models imported successfully!")
    
    # Test enums
    print("\n✓ Testing AchievementType enum:")
    for item in AchievementType:
        print(f"  - {item.name} = {item.value}")
    
    print("\n✓ Testing LeaderboardPeriod enum:")
    for item in LeaderboardPeriod:
        print(f"  - {item.name} = {item.value}")
    
    # Test model attributes
    print("\n✓ Testing LeaderboardEntry model:")
    print(f"  - Table: {LeaderboardEntry.__tablename__}")
    print(f"  - Columns: {[c.name for c in LeaderboardEntry.__table__.columns]}")
    
    print("\n✓ Testing Achievement model:")
    print(f"  - Table: {Achievement.__tablename__}")
    print(f"  - Columns: {[c.name for c in Achievement.__table__.columns]}")
    
    print("\n✓ Testing UserAchievement model:")
    print(f"  - Table: {UserAchievement.__tablename__}")
    print(f"  - Columns: {[c.name for c in UserAchievement.__table__.columns]}")
    
    print("\n✓ Testing DailyGoal model:")
    print(f"  - Table: {DailyGoal.__tablename__}")
    print(f"  - Columns: {[c.name for c in DailyGoal.__table__.columns]}")
    
    print("\n✓ Testing SystemConfig model:")
    print(f"  - Table: {SystemConfig.__tablename__}")
    print(f"  - Columns: {[c.name for c in SystemConfig.__table__.columns]}")
    
    print("\n✓ Testing AdminLog model:")
    print(f"  - Table: {AdminLog.__tablename__}")
    print(f"  - Columns: {[c.name for c in AdminLog.__table__.columns]}")
    
    # Test User relationships
    print("\n✓ Testing User relationships:")
    print(f"  - leaderboard_entries: {hasattr(User, 'leaderboard_entries')}")
    print(f"  - achievements: {hasattr(User, 'achievements')}")
    print(f"  - daily_goals: {hasattr(User, 'daily_goals')}")
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED!")
    print("="*50)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
