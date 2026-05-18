#!/usr/bin/env python3
"""Restore the MySQL auth tables used by the Node backend: users and reminders."""
import mysql.connector
import os

DB_CONFIG = dict(
    host=os.getenv('DB_HOST', 'ticketdb-ticket63.f.aivencloud.com'),
    port=int(os.getenv('DB_PORT', '13599')),
    user=os.getenv('DB_USER', 'avnadmin'),
    password=os.getenv('DB_PASSWORD', 'AVNS_QqNVFqacdQinAgGmXY9'),
    database=os.getenv('DB_NAME', 'defaultdb'),
    charset='utf8mb4',
    autocommit=True,
)

USERS_DDL = """
CREATE TABLE IF NOT EXISTS `users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_users_email` (`email`)
)
"""

REMINDERS_DDL = """
CREATE TABLE IF NOT EXISTS `reminders` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint unsigned NOT NULL,
  `title` varchar(255) NOT NULL DEFAULT 'Ticket Reminder',
  `sale_at` datetime NOT NULL,
  `offsets_minutes` json NOT NULL,
  `enabled` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_reminders_user_id` (`user_id`),
  CONSTRAINT `fk_reminders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
)
"""

USER_SEEDS = [
    (
        72,
        'lala52452452266@gmail.com',
        'pbkdf2:120000:213fd89683c9a77073ab41276941fbb8:28fc19785899fc9531b6fa7f65009ed31074eb093c731a730646d1717caab945ecc1b6ef7590a2d22aed066bcd131b5846137c826bbe2793e85dea4fec5e8b96',
        '2026-04-27 23:53:31',
        '2026-04-27 23:53:31',
    ),
]

REMINDER_SEEDS = [
    (66, 72, 'NANA MIZUKI LIVE VISION 2025-2026+ in TAIPEI', '2026-04-11 17:30:00', '[60, 30, 10]', 1, '2026-04-28 02:37:40', '2026-04-28 02:37:40'),
    (67, 72, 'NANA MIZUKI LIVE VISION 2025-2026+ in TAIPEI', '2026-04-11 17:30:00', '[60, 30, 10]', 1, '2026-04-28 04:16:27', '2026-04-28 04:16:27'),
    (68, 72, 'NANA MIZUKI LIVE VISION 2025-2026+ in TAIPEI', '2026-04-11 17:30:00', '[60, 30, 10]', 1, '2026-04-28 04:16:28', '2026-04-28 04:16:28'),
    (69, 72, 'NANA MIZUKI LIVE VISION 2025-2026+ in TAIPEI', '2026-04-11 17:30:00', '[60, 30, 10]', 1, '2026-04-28 04:16:28', '2026-04-28 04:16:28'),
    (70, 72, 'NANA MIZUKI LIVE VISION 2025-2026+ in TAIPEI', '2026-04-11 17:30:00', '[60, 30, 10]', 1, '2026-04-28 04:17:16', '2026-04-28 04:17:16'),
    (71, 72, 'Chihiro Yonekura 30th Anniversary Asia Tour 2026', '2026-03-28 12:00:00', '[60, 30, 10]', 1, '2026-04-28 04:17:26', '2026-04-28 04:17:26'),
    (72, 72, 'Leina Live Tour 2026 “Jellyfish” in Taipei', '2026-05-02 11:00:00', '[60, 30, 10]', 1, '2026-04-28 04:52:06', '2026-04-28 04:52:06'),
]


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        cur.execute(USERS_DDL)
        cur.execute(REMINDERS_DDL)

        for row in USER_SEEDS:
            cur.execute(
                """
                INSERT INTO `users` (`id`,`email`,`password_hash`,`created_at`,`updated_at`)
                VALUES (%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    `email`=VALUES(`email`),
                    `password_hash`=VALUES(`password_hash`),
                    `created_at`=VALUES(`created_at`),
                    `updated_at`=VALUES(`updated_at`)
                """,
                row,
            )

        for row in REMINDER_SEEDS:
            cur.execute(
                """
                INSERT INTO `reminders`
                (`id`,`user_id`,`title`,`sale_at`,`offsets_minutes`,`enabled`,`created_at`,`updated_at`)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    `user_id`=VALUES(`user_id`),
                    `title`=VALUES(`title`),
                    `sale_at`=VALUES(`sale_at`),
                    `offsets_minutes`=VALUES(`offsets_minutes`),
                    `enabled`=VALUES(`enabled`),
                    `created_at`=VALUES(`created_at`),
                    `updated_at`=VALUES(`updated_at`)
                """,
                row,
            )

        conn.commit()
        print('restored users and reminders tables')
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
