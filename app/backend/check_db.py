import sqlite3

conn = sqlite3.connect('data/vigilai.db')
cursor = conn.cursor()

# 按信息源统计
cursor.execute('SELECT source_id, COUNT(*) as count FROM activities GROUP BY source_id')
print('按信息源统计:')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

# 华为开发者活动示例
cursor.execute('SELECT source_id, title, url FROM activities WHERE source_id = "huawei_dev" LIMIT 5')
print('\n华为开发者活动示例:')
for row in cursor.fetchall():
    print(f'{row[0]} - {row[1][:50]} - {row[2][:50]}')

conn.close()
