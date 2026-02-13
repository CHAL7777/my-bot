#!/usr/bin/env python3
"""
Seed Sample Questions Script - Telegram Quiz Bot
Creates sample subjects, chapters, and questions for testing.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import init_db, get_db, AsyncSessionLocal
from app.db.models import Subject, Chapter, Question
from app.repositories.question_repo import QuestionRepository

# Sample data
SAMPLE_SUBJECTS = [
    {"name": "Mathematics", "description": "Basic mathematics questions"},
    {"name": "Physics", "description": "Physics fundamentals"},
    {"name": "Chemistry", "description": "Chemistry basics"},
]

# Sample chapters per subject
SAMPLE_CHAPTERS = {
    "Mathematics": [
        {"name": "Addition", "order": 1},
        {"name": "Subtraction", "order": 2},
        {"name": "Multiplication", "order": 3},
        {"name": "Division", "order": 4},
    ],
    "Physics": [
        {"name": "Motion", "order": 1},
        {"name": "Force", "order": 2},
        {"name": "Energy", "order": 3},
    ],
    "Chemistry": [
        {"name": "Atomic Structure", "order": 1},
        {"name": "Periodic Table", "order": 2},
        {"name": "Chemical Bonds", "order": 3},
    ],
}

# Sample questions - simple difficulty
SAMPLE_QUESTIONS = {
    ("Mathematics", "Addition"): [
        {
            "question_text": "What is 5 + 7?",
            "option_a": "10",
            "option_b": "12",
            "option_c": "14",
            "option_d": "15",
            "correct_option": "B",
            "explanation": "5 + 7 = 12"
        },
        {
            "question_text": "What is 8 + 6?",
            "option_a": "12",
            "option_b": "13",
            "option_c": "14",
            "option_d": "15",
            "correct_option": "C",
            "explanation": "8 + 6 = 14"
        },
        {
            "question_text": "What is 9 + 4?",
            "option_a": "12",
            "option_b": "13",
            "option_c": "14",
            "option_d": "11",
            "correct_option": "B",
            "explanation": "9 + 4 = 13"
        },
    ],
    ("Mathematics", "Subtraction"): [
        {
            "question_text": "What is 15 - 7?",
            "option_a": "6",
            "option_b": "7",
            "option_c": "8",
            "option_d": "9",
            "correct_option": "C",
            "explanation": "15 - 7 = 8"
        },
        {
            "question_text": "What is 20 - 9?",
            "option_a": "10",
            "option_b": "11",
            "option_c": "12",
            "option_d": "13",
            "correct_option": "B",
            "explanation": "20 - 9 = 11"
        },
    ],
    ("Mathematics", "Multiplication"): [
        {
            "question_text": "What is 6 × 7?",
            "option_a": "36",
            "option_b": "42",
            "option_c": "48",
            "option_d": "54",
            "correct_option": "B",
            "explanation": "6 × 7 = 42"
        },
        {
            "question_text": "What is 8 × 5?",
            "option_a": "35",
            "option_b": "40",
            "option_c": "45",
            "option_d": "50",
            "correct_option": "B",
            "explanation": "8 × 5 = 40"
        },
    ],
    ("Mathematics", "Division"): [
        {
            "question_text": "What is 48 ÷ 6?",
            "option_a": "6",
            "option_b": "7",
            "option_c": "8",
            "option_d": "9",
            "correct_option": "C",
            "explanation": "48 ÷ 6 = 8"
        },
        {
            "question_text": "What is 72 ÷ 8?",
            "option_a": "7",
            "option_b": "8",
            "option_c": "9",
            "option_d": "10",
            "correct_option": "C",
            "explanation": "72 ÷ 8 = 9"
        },
    ],
    ("Physics", "Motion"): [
        {
            "question_text": "What is the SI unit of speed?",
            "option_a": "Meter",
            "option_b": "Second",
            "option_c": "Meter per second",
            "option_d": "Kilogram",
            "correct_option": "C",
            "explanation": "Speed is measured in meters per second (m/s)"
        },
        {
            "question_text": "What is velocity?",
            "option_a": "Distance traveled",
            "option_b": "Speed in a specific direction",
            "option_c": "Time taken",
            "option_d": "Mass",
            "correct_option": "B",
            "explanation": "Velocity is speed with a specific direction"
        },
    ],
    ("Physics", "Force"): [
        {
            "question_text": "What is Newton's first law also known as?",
            "option_a": "Law of acceleration",
            "option_b": "Law of inertia",
            "option_c": "Law of action-reaction",
            "option_d": "Law of gravity",
            "correct_option": "B",
            "explanation": "Newton's first law is the law of inertia"
        },
        {
            "question_text": "What is the unit of force?",
            "option_a": "Newton",
            "option_b": "Joule",
            "option_c": "Watt",
            "option_d": "Pascal",
            "correct_option": "A",
            "explanation": "Force is measured in Newtons (N)"
        },
    ],
    ("Physics", "Energy"): [
        {
            "question_text": "What is kinetic energy?",
            "option_a": "Energy of position",
            "option_b": "Energy of motion",
            "option_c": "Energy of heat",
            "option_d": "Energy of light",
            "correct_option": "B",
            "explanation": "Kinetic energy is the energy of motion"
        },
        {
            "question_text": "What is the unit of energy?",
            "option_a": "Newton",
            "option_b": "Joule",
            "option_c": "Watt",
            "option_d": "Pascal",
            "correct_option": "B",
            "explanation": "Energy is measured in Joules (J)"
        },
    ],
    ("Chemistry", "Atomic Structure"): [
        {
            "question_text": "What is the center of an atom called?",
            "option_a": "Nucleus",
            "option_b": "Electron",
            "option_c": "Proton",
            "option_d": "Neutron",
            "correct_option": "A",
            "explanation": "The nucleus is the center of an atom containing protons and neutrons"
        },
        {
            "question_text": "Which particle has a positive charge?",
            "option_a": "Electron",
            "option_b": "Neutron",
            "option_c": "Proton",
            "option_d": "Ion",
            "correct_option": "C",
            "explanation": "Protons have a positive charge"
        },
    ],
    ("Chemistry", "Periodic Table"): [
        {
            "question_text": "What is the atomic number of Hydrogen?",
            "option_a": "1",
            "option_b": "2",
            "option_c": "8",
            "option_d": "6",
            "correct_option": "A",
            "explanation": "Hydrogen has atomic number 1"
        },
        {
            "question_text": "How many periods are in the periodic table?",
            "option_a": "5",
            "option_b": "6",
            "option_c": "7",
            "option_d": "8",
            "correct_option": "C",
            "explanation": "There are 7 periods in the periodic table"
        },
    ],
    ("Chemistry", "Chemical Bonds"): [
        {
            "question_text": "What type of bond forms when electrons are shared?",
            "option_a": "Ionic bond",
            "option_b": "Covalent bond",
            "option_c": "Metallic bond",
            "option_d": "Hydrogen bond",
            "correct_option": "B",
            "explanation": "Covalent bonds form when atoms share electrons"
        },
        {
            "question_text": "What is formed when electrons are transferred?",
            "option_a": "Covalent bond",
            "option_b": "Ionic bond",
            "option_c": "Metallic bond",
            "option_d": "Coordinate bond",
            "correct_option": "B",
            "explanation": "Ionic bonds form through electron transfer"
        },
    ],
}


async def seed_database():
    """Seed the database with sample data"""
    print("Initializing database...")
    await init_db()
    
    async with AsyncSessionLocal() as session:
        repo = QuestionRepository(session)
        
        # Create subjects
        subject_map = {}
        for subject_data in SAMPLE_SUBJECTS:
            # Check if subject exists
            subject = await repo.get_subject_by_name(subject_data["name"])
            if not subject:
                subject = await repo.create_subject(
                    subject_name=subject_data["name"],
                    description=subject_data["description"]
                )
                print(f"Created subject: {subject_data['name']}")
            else:
                print(f"Subject already exists: {subject_data['name']}")
            subject_map[subject_data["name"]] = subject
        
        # Create chapters
        chapter_map = {}
        for subject_name, chapters in SAMPLE_CHAPTERS.items():
            subject = subject_map.get(subject_name)
            if not subject:
                continue
                
            for chapter_data in chapters:
                # Check if chapter exists
                existing_chapters = await repo.get_chapters(subject.subject_id)
                chapter = next(
                    (c for c in existing_chapters if c.chapter_name == chapter_data["name"]),
                    None
                )
                if not chapter:
                    chapter = await repo.create_chapter(
                        subject_id=subject.subject_id,
                        chapter_name=chapter_data["name"],
                        chapter_order=chapter_data["order"]
                    )
                    print(f"  Created chapter: {chapter_data['name']}")
                else:
                    print(f"  Chapter already exists: {chapter_data['name']}")
                
                chapter_map[(subject_name, chapter_data["name"])] = chapter
        
        # Create questions
        question_count = 0
        for (subject_name, chapter_name), questions in SAMPLE_QUESTIONS.items():
            chapter = chapter_map.get((subject_name, chapter_name))
            if not chapter:
                print(f"Warning: Chapter {chapter_name} not found for subject {subject_name}")
                continue
            
            for q_data in questions:
                # Check if question already exists (simplified check)
                existing = await repo.get_random_questions(
                    subject_id=chapter.subject_id,
                    chapter_id=chapter.chapter_id,
                    difficulty='simple',
                    limit=100
                )
                
                # Simple duplicate check based on question text
                if not any(q.get('question_text') == q_data['question_text'] for q in existing):
                    await repo.create_question(
                        subject_id=chapter.subject_id,
                        chapter_id=chapter.chapter_id,
                        difficulty='simple',
                        question_text=q_data['question_text'],
                        option_a=q_data['option_a'],
                        option_b=q_data['option_b'],
                        option_c=q_data['option_c'],
                        option_d=q_data['option_d'],
                        correct_option=q_data['correct_option'],
                        explanation=q_data.get('explanation')
                    )
                    question_count += 1
                    print(f"    Created question: {q_data['question_text'][:50]}...")
                else:
                    print(f"    Question already exists: {q_data['question_text'][:50]}...")
        
        print(f"\n✅ Seed completed! Created {question_count} new questions")
        
        # Print summary
        print("\n--- Database Summary ---")
        total = await repo.get_question_count()
        simple = await repo.get_question_count(difficulty='simple')
        medium = await repo.get_question_count(difficulty='medium')
        hard = await repo.get_question_count(difficulty='hard')
        
        print(f"Total questions: {total}")
        print(f"  - Simple: {simple}")
        print(f"  - Medium: {medium}")
        print(f"  - Hard: {hard}")
        
        subjects = await repo.get_subjects()
        print(f"\nSubjects: {len(subjects)}")
        for subject in subjects:
            count = await repo.get_question_count(subject_id=subject.subject_id)
            print(f"  - {subject.subject_name}: {count} questions")


async def clear_database():
    """Clear all questions (for testing)"""
    print("Clearing database...")
    await init_db()
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import delete
        
        # Delete in reverse order of dependencies
        await session.execute(delete(Question))
        await session.execute(delete(Chapter))
        await session.execute(delete(Subject))
        await session.commit()
        
        print("Database cleared!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed or clear sample data")
    parser.add_argument("--clear", action="store_true", help="Clear all data instead of seeding")
    args = parser.parse_args()
    
    if args.clear:
        asyncio.run(clear_database())
    else:
        asyncio.run(seed_database())


if __name__ == "__main__":
    main()

