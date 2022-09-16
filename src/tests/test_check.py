import redis
import psycopg2

def test_check():
    assert True

def test_check2():
    assert True

def test_check3():
    assert True

def test_check4():
    assert True

def test_check_redis():
    r = redis.Redis(host='redis', port=6379, db=0)
    assert r.set('foo', 'bar') == True
    assert r.get('foo') == b'bar'

def test_check_db():
    database = psycopg2.connect(
        " ".join(
            [
                f"dbname=default",
                f"user=postgres",
                f"password=postgres",
                f"host=db",
                f"port=5432",
            ]
        )
    )
    try:
        with database.cursor() as cursor:
            cursor.execute("select 1;")
    finally:
        database.close()
