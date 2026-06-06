from __future__ import annotations

import argparse
import asyncio
import random
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

from faker import Faker
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.agent import Agent  # noqa: F401
from app.models.base import Base
from app.models.post import Post, PostStatus
from app.models.user import User, UserRole


DEFAULT_USER_COUNT = 1000
DEFAULT_POST_COUNT = 10000
DEFAULT_BATCH_SIZE = 1000
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "app.db"

POST_CATEGORIES = ("tech", "product", "ops", "notice")


def chunked(items: list[dict], size: int) -> Iterable[list[dict]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def maybe_none(value, probability: float = 0.15):
    return None if random.random() < probability else value


def build_users(fake: Faker, count: int, run_id: str) -> list[dict]:
    users = []
    roles = tuple(role.value for role in UserRole)
    for index in range(1, count + 1):
        users.append(
            {
                "name": fake.name()[:50],
                "email": f"demo-{run_id}-{index}@example.test",
                "phone": fake.phone_number()[:30],
                "bio": fake.paragraph(nb_sentences=2),
                "age": random.randint(18, 75),
                "account_balance": round(random.uniform(0, 100000), 2),
                "birthday": fake.date_between(start_date="-75y", end_date="-18y"),
                "role": random.choice(roles),
                "is_active": random.random() > 0.08,
                "is_staff": random.random() < 0.12,
                "last_login_at": maybe_none(
                    fake.date_time_between(start_date="-180d", end_date="now"),
                    probability=0.18,
                ),
            }
        )
    return users


def build_posts(fake: Faker, count: int, author_ids: list[int]) -> list[dict]:
    posts = []
    statuses = tuple(status.value for status in PostStatus)
    for _ in range(count):
        status = random.choice(statuses)
        is_published = status == PostStatus.PUBLISHED.value or random.random() < 0.25
        published_at = (
            fake.date_time_between(start_date="-365d", end_date="now")
            if is_published
            else None
        )
        posts.append(
            {
                "title": fake.sentence(nb_words=random.randint(4, 10)).rstrip(".")[
                    :200
                ],
                "summary": fake.paragraph(nb_sentences=2),
                "content": fake.paragraph(nb_sentences=random.randint(6, 14))[:1000],
                "category": random.choice(POST_CATEGORIES),
                "status": status,
                "is_published": is_published,
                "view_count": random.randint(0, 250000),
                "rating": round(random.uniform(0, 5), 1),
                "priority": random.randint(0, 10),
                "publish_date": published_at.date() if published_at else None,
                "published_at": published_at,
                "author_id": random.choice(author_ids),
            }
        )
    return posts


async def insert_batches(session, model, rows: list[dict], batch_size: int) -> None:
    for batch in chunked(rows, batch_size):
        await session.execute(insert(model), batch)


async def seed_data(args: argparse.Namespace) -> None:
    db_url = args.database_url or f"sqlite+aiosqlite:///{args.db_path}"
    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    fake = Faker(args.locale)
    Faker.seed(args.seed)
    random.seed(args.seed)
    run_id = uuid4().hex[:10]

    async with engine.begin() as conn:
        if args.reset:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        users = build_users(fake, args.users, run_id)
        await insert_batches(session, User, users, args.batch_size)
        await session.commit()

        result = await session.execute(
            select(User.id)
            .where(User.email.like(f"demo-{run_id}-%@example.test"))
            .order_by(User.id)
        )
        author_ids = list(result.scalars())
        if args.posts and not author_ids:
            raise RuntimeError("没有可用的作者，无法生成文章。")

        posts = build_posts(fake, args.posts, author_ids)
        await insert_batches(session, Post, posts, args.batch_size)
        await session.commit()

    await engine.dispose()
    print(
        f"Seeded {len(users)} users and {len(posts)} posts into {db_url} "
        f"(run_id={run_id})."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo users and posts.")
    parser.add_argument("--users", type=int, default=DEFAULT_USER_COUNT)
    parser.add_argument("--posts", type=int, default=DEFAULT_POST_COUNT)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--locale", default="zh_CN")
    parser.add_argument("--seed", type=int, default=20260606)
    parser.add_argument(
        "--reset", action="store_true", help="重建 demo 数据表后再插入。"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="SQLite 数据库路径；默认使用项目根目录 app.db。",
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="完整 SQLAlchemy database URL；设置后会覆盖 --db-path。",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(seed_data(parse_args()))
